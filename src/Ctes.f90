module Ctes
    implicit none

    ! Runtime-configurable simulation parameters.
    integer :: N = 100                           ! Number of primary particles (PP)
    real    :: Df = 1.79                         ! Fractal dimension
    real    :: kf = 1.40                         ! Fractal prefactor
    real    :: rp_g = 15.0                       ! Geometric mean PP radius
    real    :: rp_gstd = 1.00                    ! Geometric PP standard deviation
    integer :: Quantity_aggregates = 1           ! Number of aggregates to generate
    integer :: Ext_case = 0                      ! Activate extreme cases (0=no, 1=yes)
    real    :: Nsubcl_perc = 0.10                ! Initial sub-cluster size as fraction of N
    real    :: tol_ov = 1.0e-6                   ! Numerical tolerance for unintended overlap
    integer :: random_seed_value = -1            ! -1 = processor/OS default, >=0 = reproducible seed
    character(len=256) :: output_dir = 'results' ! Directory for aggregate .dat files

    ! Intended contact-overlap model. Fractions are dimensionless relative to Ri+Rj.
    ! none        : particles touch (legacy FracVAL behavior)
    ! fixed       : each intended contact uses overlap_fraction
    ! statistical : each intended contact is sampled from a bounded normal distribution
    character(len=16) :: overlap_mode = 'none'
    real :: overlap_fraction = 0.0
    real :: overlap_mean = 0.05
    real :: overlap_std = 0.02
    real :: overlap_max = 0.12

    ! True mathematical constant: this remains compile-time.
    real, parameter :: pi = 4.0*atan(1.0)

    ! N is a runtime setting, so N-sized arrays are allocated after input is read.
    real, allocatable :: R(:)
    real, allocatable :: X(:), Y(:), Z(:)

    ! One intended contact is formed per tree edge; a completed N-particle aggregate
    ! therefore has N-1 entries. This history is exposed to Python and sidecar output.
    real, allocatable :: contact_overlaps(:)
    integer :: contact_count = 0

    integer:: iter, i, j, k

contains

    subroutine load_config(filename)
        character(len=*), intent(in) :: filename
        integer :: unit_number, ios
        character(len=512) :: iomsg_text

        namelist /fracval/ N, Df, kf, rp_g, rp_gstd, Quantity_aggregates, &
                           Ext_case, Nsubcl_perc, tol_ov, random_seed_value, output_dir, &
                           overlap_mode, overlap_fraction, overlap_mean, overlap_std, overlap_max

        unit_number = 20
        open(unit=unit_number, file=trim(filename), status='old', action='read', &
             iostat=ios, iomsg=iomsg_text)
        if (ios /= 0) then
            write(*,'(A)') 'ERROR: Could not open input file: '//trim(filename)
            write(*,'(A)') '       '//trim(iomsg_text)
            write(*,'(A)') 'Run with --help for usage information.'
            stop 1
        end if

        read(unit_number, nml=fracval, iostat=ios, iomsg=iomsg_text)
        close(unit_number)

        if (ios /= 0) then
            write(*,'(A)') 'ERROR: Could not read &fracval input from: '//trim(filename)
            write(*,'(A)') '       '//trim(iomsg_text)
            write(*,'(A)') 'Check the syntax against the supplied fracval.in example.'
            stop 1
        end if

        output_dir = trim(adjustl(output_dir))
        overlap_mode = trim(adjustl(lowercase(overlap_mode)))
        call validate_config()
        call allocate_particle_arrays()
        call ensure_output_directory()
    end subroutine load_config


    subroutine validate_config()
        character(len=16) :: mode

        if (N < 5) then
            write(*,'(A,I0)') 'ERROR: N must be at least 5. Received N = ', N
            stop 1
        end if

        if (Df <= 0.0) then
            write(*,'(A,ES12.4)') 'ERROR: Df must be greater than 0. Received Df = ', Df
            stop 1
        end if

        if (kf <= 0.0) then
            write(*,'(A,ES12.4)') 'ERROR: kf must be greater than 0. Received kf = ', kf
            stop 1
        end if

        if (rp_g <= 0.0) then
            write(*,'(A,ES12.4)') 'ERROR: rp_g must be greater than 0. Received rp_g = ', rp_g
            stop 1
        end if

        if (rp_gstd < 1.0) then
            write(*,'(A,ES12.4)') 'ERROR: rp_gstd must be >= 1. Received rp_gstd = ', rp_gstd
            stop 1
        end if

        if (Quantity_aggregates < 1) then
            write(*,'(A,I0)') 'ERROR: Quantity_aggregates must be at least 1. Received = ', &
                               Quantity_aggregates
            stop 1
        end if

        if (Ext_case /= 0 .and. Ext_case /= 1) then
            write(*,'(A,I0)') 'ERROR: Ext_case must be 0 or 1. Received Ext_case = ', Ext_case
            stop 1
        end if

        if (Nsubcl_perc <= 0.0 .or. Nsubcl_perc > 1.0) then
            write(*,'(A,ES12.4)') 'ERROR: Nsubcl_perc must be in (0,1]. Received = ', &
                                   Nsubcl_perc
            stop 1
        end if

        if (N >= 50 .and. N <= 500 .and. int(Nsubcl_perc*real(N)) < 1) then
            write(*,'(A)') 'ERROR: Nsubcl_perc*N must produce at least one particle per sub-cluster.'
            stop 1
        end if

        if (tol_ov <= 0.0) then
            write(*,'(A,ES12.4)') 'ERROR: tol_ov must be greater than 0. Received tol_ov = ', tol_ov
            stop 1
        end if

        if (random_seed_value < -1) then
            write(*,'(A,I0)') 'ERROR: random_seed_value must be -1 or >= 0. Received = ', random_seed_value
            stop 1
        end if

        if (len_trim(output_dir) == 0) then
            write(*,'(A)') 'ERROR: output_dir must not be empty.'
            stop 1
        end if

        if (index(output_dir, '"') > 0 .or. index(output_dir, '''') > 0 .or. &
            index(output_dir, ';') > 0 .or. index(output_dir, '|') > 0 .or. &
            index(output_dir, '&') > 0 .or. index(output_dir, '<') > 0 .or. &
            index(output_dir, '>') > 0) then
            write(*,'(A)') 'ERROR: output_dir contains unsupported shell metacharacters.'
            stop 1
        end if

        mode = trim(lowercase(overlap_mode))
        if (mode /= 'none' .and. mode /= 'fixed' .and. mode /= 'statistical' .and. mode /= 'normal') then
            write(*,'(A)') "ERROR: overlap_mode must be 'none', 'fixed', or 'statistical'."
            stop 1
        end if

        if (overlap_fraction < 0.0 .or. overlap_fraction >= 0.95) then
            write(*,'(A,F10.4)') 'ERROR: overlap_fraction must be in [0,0.95). Received = ', overlap_fraction
            stop 1
        end if

        if (overlap_mean < 0.0 .or. overlap_mean >= 0.95) then
            write(*,'(A,F10.4)') 'ERROR: overlap_mean must be in [0,0.95). Received = ', overlap_mean
            stop 1
        end if

        if (overlap_std < 0.0) then
            write(*,'(A,F10.4)') 'ERROR: overlap_std must be >= 0. Received = ', overlap_std
            stop 1
        end if

        if (overlap_max <= 0.0 .or. overlap_max >= 0.95) then
            write(*,'(A,F10.4)') 'ERROR: overlap_max must be in (0,0.95). Received = ', overlap_max
            stop 1
        end if

        if ((mode == 'statistical' .or. mode == 'normal') .and. overlap_mean > overlap_max) then
            write(*,'(A)') 'ERROR: overlap_mean must not exceed overlap_max in statistical mode.'
            stop 1
        end if
    end subroutine validate_config


    subroutine allocate_particle_arrays()
        if (allocated(R)) deallocate(R)
        if (allocated(X)) deallocate(X)
        if (allocated(Y)) deallocate(Y)
        if (allocated(Z)) deallocate(Z)
        if (allocated(contact_overlaps)) deallocate(contact_overlaps)

        allocate(R(N), X(N), Y(N), Z(N))
        allocate(contact_overlaps(max(1, N-1)))
        call reset_contact_overlaps()
    end subroutine allocate_particle_arrays


    subroutine reset_contact_overlaps()
        contact_count = 0
        if (allocated(contact_overlaps)) contact_overlaps = 0.0
    end subroutine reset_contact_overlaps


    subroutine record_contact_overlap(value)
        real, intent(in) :: value

        if (.not. allocated(contact_overlaps)) return
        if (contact_count >= size(contact_overlaps)) return
        contact_count = contact_count + 1
        contact_overlaps(contact_count) = value
    end subroutine record_contact_overlap


    real function sample_contact_overlap() result(value)
        real :: u1, u2, z, candidate
        integer :: attempt
        character(len=16) :: mode

        mode = trim(lowercase(overlap_mode))
        select case (mode)
        case ('none')
            value = 0.0
        case ('fixed')
            value = overlap_fraction
        case ('statistical', 'normal')
            if (overlap_std <= 0.0) then
                value = max(0.0, min(overlap_max, overlap_mean))
                return
            end if

            ! Rejection sample a normal distribution bounded to [0, overlap_max].
            ! A hard fallback avoids an infinite loop for pathological inputs.
            do attempt = 1, 1000
                call random_number(u1)
                call random_number(u2)
                if (u1 <= tiny(1.0)) cycle
                z = sqrt(-2.0*log(u1))*cos(2.0*pi*u2)
                candidate = overlap_mean + overlap_std*z
                if (candidate >= 0.0 .and. candidate <= overlap_max) then
                    value = candidate
                    return
                end if
            end do
            value = max(0.0, min(overlap_max, overlap_mean))
        case default
            value = 0.0
        end select
    end function sample_contact_overlap


    subroutine set_overlap_mode_from_code(code)
        integer, intent(in) :: code
        select case (code)
        case (0)
            overlap_mode = 'none'
        case (1)
            overlap_mode = 'fixed'
        case (2)
            overlap_mode = 'statistical'
        case default
            overlap_mode = 'invalid'
        end select
    end subroutine set_overlap_mode_from_code


    integer function overlap_mode_code() result(code)
        character(len=16) :: mode
        mode = trim(lowercase(overlap_mode))
        select case (mode)
        case ('none')
            code = 0
        case ('fixed')
            code = 1
        case ('statistical', 'normal')
            code = 2
        case default
            code = -1
        end select
    end function overlap_mode_code


    subroutine ensure_output_directory()
        character(len=1024) :: command
        character(len=256) :: native_dir
        character(len=64) :: os_name
        integer :: exitstat, cmdstat, envstat, idx

        os_name = ''
        call get_environment_variable('OS', os_name, status=envstat)

        if (envstat == 0 .and. index(os_name, 'Windows_NT') > 0) then
            ! cmd.exe treats '/' as a switch prefix, so hand it a native path.
            native_dir = output_dir
            do idx = 1, len_trim(native_dir)
                if (native_dir(idx:idx) == '/') native_dir(idx:idx) = '\'
            end do
            command = 'if not exist "'//trim(native_dir)//'" mkdir "'//trim(native_dir)//'"'
        else
            command = 'mkdir -p "'//trim(output_dir)//'"'
        end if

        call execute_command_line(trim(command), wait=.true., exitstat=exitstat, cmdstat=cmdstat)

        if (cmdstat /= 0 .or. exitstat /= 0) then
            write(*,'(A)') 'ERROR: Could not create output directory: '//trim(output_dir)
            stop 1
        end if
    end subroutine ensure_output_directory


    subroutine print_config(filename)
        character(len=*), intent(in) :: filename

        write(*,'(A)') 'FracVAL runtime configuration'
        write(*,'(A)') '  input file          : '//trim(filename)
        write(*,'(A,I0)') '  N                   : ', N
        write(*,'(A,F10.4)') '  Df                  : ', Df
        write(*,'(A,F10.4)') '  kf                  : ', kf
        write(*,'(A,F10.4)') '  rp_g                : ', rp_g
        write(*,'(A,F10.4)') '  rp_gstd             : ', rp_gstd
        write(*,'(A,I0)') '  Quantity_aggregates : ', Quantity_aggregates
        write(*,'(A,I0)') '  Ext_case            : ', Ext_case
        write(*,'(A,F10.4)') '  Nsubcl_perc         : ', Nsubcl_perc
        write(*,'(A,ES12.4)') '  tol_ov              : ', tol_ov
        write(*,'(A,I0)') '  random_seed_value   : ', random_seed_value
        write(*,'(A)') '  overlap_mode        : '//trim(overlap_mode)
        if (trim(overlap_mode) == 'fixed') then
            write(*,'(A,F10.4)') '  overlap_fraction    : ', overlap_fraction
        else if (trim(overlap_mode) == 'statistical' .or. trim(overlap_mode) == 'normal') then
            write(*,'(A,F10.4)') '  overlap_mean        : ', overlap_mean
            write(*,'(A,F10.4)') '  overlap_std         : ', overlap_std
            write(*,'(A,F10.4)') '  overlap_max         : ', overlap_max
        end if
        write(*,'(A)') '  output_dir          : '//trim(output_dir)
        write(*,'(A)') ''
    end subroutine print_config


    subroutine print_overlap_summary()
        real :: mean_value, std_value

        if (contact_count <= 0) return
        mean_value = sum(contact_overlaps(1:contact_count))/real(contact_count)
        if (contact_count > 1) then
            std_value = sqrt(sum((contact_overlaps(1:contact_count)-mean_value)**2)/real(contact_count-1))
        else
            std_value = 0.0
        end if
        write(*,'(A,I0)') 'Intended contacts: ', contact_count
        write(*,'(A,F8.3,A)') 'Mean contact overlap: ', 100.0*mean_value, ' %'
        write(*,'(A,F8.3,A)') 'Std. contact overlap: ', 100.0*std_value, ' %'
        write(*,'(A,F8.3,A)') 'Max contact overlap: ', 100.0*maxval(contact_overlaps(1:contact_count)), ' %'
    end subroutine print_overlap_summary


    subroutine initialize_rng(seed_value)
        use iso_fortran_env, only: int64
        integer, intent(in) :: seed_value
        integer :: nseed, idx
        integer, allocatable :: seed_put(:)
        integer(int64) :: base, value64, modulus64

        if (seed_value < 0) then
            call random_seed()
            return
        end if

        call random_seed(size=nseed)
        allocate(seed_put(nseed))
        modulus64 = 2147483646_int64
        base = int(seed_value, int64)

        do idx = 1, nseed
            value64 = modulo(base + 104729_int64*int(idx, int64) + &
                             7919_int64*int(idx, int64)*int(idx, int64), modulus64)
            seed_put(idx) = int(value64 + 1_int64)
        end do

        call random_seed(put=seed_put)
        deallocate(seed_put)
    end subroutine initialize_rng


    pure function lowercase(text) result(out)
        character(len=*), intent(in) :: text
        character(len=len(text)) :: out
        integer :: idx, code

        out = text
        do idx = 1, len(text)
            code = iachar(out(idx:idx))
            if (code >= iachar('A') .and. code <= iachar('Z')) then
                out(idx:idx) = achar(code + 32)
            end if
        end do
    end function lowercase

end module Ctes
