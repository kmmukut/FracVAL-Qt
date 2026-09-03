! FracVAL: An Improved Tunable Algorithm of Cluster-Cluster Aggregation for
! Generation of Fractal Structures Formed by Polydisperse Primary Particles
!
! This is the cluster-cluster (CC) aggregation algorithm.
! Developed by: J. Moran, A. Fuentes, F. Liu and J. Yon
! Universidad Tecnica Federico Santa Maria, Chile.
!
! Runtime interface added so simulation parameters can be changed without
! recompiling the source code.

program Frac_VAL_CCA
use Ctes                ! runtime configuration and shared arrays
use a_Random_PP         ! random primary particles generation
use RAND_SAMPLE         ! random sample without replacement from a vector
use CCA_module          ! Cluster-Cluster aggregation algorithm
implicit none

logical :: not_able_cca, not_able_pca
character(len=512) :: input_file, arg1
integer :: nargs

input_file = 'fracval.in'
nargs = command_argument_count()

if (nargs > 0) then
    call get_command_argument(1, arg1)

    if (trim(arg1) == '--help' .or. trim(arg1) == '-h') then
        call print_usage()
        stop
    else
        input_file = trim(arg1)
    end if
end if

if (nargs > 1) then
    write(*,'(A)') 'ERROR: Too many command-line arguments.'
    call print_usage()
    stop 1
end if

call load_config(trim(input_file))
call print_config(trim(input_file))
call initialize_rng(random_seed_value)

not_able_cca = .false.
not_able_pca = .false.
iter = 1

do while (iter <= Quantity_aggregates)

    R = lognormal_pp_radii(rp_gstd,rp_g,N)
    R = randsample(R,N)

    write(*,'(A,I0,A,I0)') 'Aggregate ', iter, '/', Quantity_aggregates

    call reset_contact_overlaps()
    call CCA_sub(not_able_cca,not_able_pca)

    if (not_able_pca) then
        write(*,'(A)') 'Restarting aggregation process (PC not able to continue)'
    elseif (not_able_cca) then
        write(*,'(A)') 'Restarting aggregation process (CC not able to continue)'
    else
        call print_overlap_summary()
        iter = iter + 1
    end if

end do

write(*,'(A)') 'Finished successfully'
write(*,'(A)') 'Results: '//trim(output_dir)

contains

    subroutine print_usage()
        write(*,'(A)') 'Usage:'
        write(*,'(A)') '  fracval [input-file]'
        write(*,'(A)') ''
        write(*,'(A)') 'If input-file is omitted, FracVAL reads ./fracval.in.'
        write(*,'(A)') 'Simulation parameters are read at runtime; recompilation is only'
        write(*,'(A)') 'needed after changing the Fortran source code.'
        write(*,'(A)') ''
        write(*,'(A)') 'Examples:'
        write(*,'(A)') '  ./build/fracval'
        write(*,'(A)') '  ./build/fracval tests/monodisperse/fracval.in'
        write(*,'(A)') '  ./build/fracval --help'
    end subroutine print_usage

end program Frac_VAL_CCA
