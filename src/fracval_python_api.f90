! Thin F2PY-facing wrapper around the existing FracVAL Fortran engine.
!
! The wrapper exposes scalar runtime inputs, particle arrays, and the realized
! intended-contact overlap fractions. The PCA/CCA modules remain the numerical
! core.

subroutine fracval_generate(n_in, df_in, kf_in, rp_g_in, rp_gstd_in, &
                            ext_case_in, nsubcl_perc_in, tol_ov_in, seed_in, &
                            max_attempts, overlap_mode_in, overlap_fraction_in, &
                            overlap_mean_in, overlap_std_in, overlap_max_in, &
                            x_out, y_out, z_out, r_out, contact_overlap_out, &
                            n_contacts, status, attempts)
    use Ctes
    use a_Random_PP
    use RAND_SAMPLE
    use CCA_module
    implicit none

    integer, intent(in) :: n_in, ext_case_in, seed_in, max_attempts, overlap_mode_in
    real, intent(in) :: df_in, kf_in, rp_g_in, rp_gstd_in, nsubcl_perc_in, tol_ov_in
    real, intent(in) :: overlap_fraction_in, overlap_mean_in, overlap_std_in, overlap_max_in
    real, intent(out) :: x_out(n_in), y_out(n_in), z_out(n_in), r_out(n_in)
    real, intent(out) :: contact_overlap_out(n_in)
    integer, intent(out) :: n_contacts, status, attempts

    logical :: not_able_cca, not_able_pca

    x_out = 0.0
    y_out = 0.0
    z_out = 0.0
    r_out = 0.0
    contact_overlap_out = 0.0
    n_contacts = 0
    status = 0
    attempts = 0

    ! Validate inputs without STOP so Python receives an error code.
    if (n_in < 5) then
        status = 1
        return
    end if
    if (df_in <= 0.0 .or. kf_in <= 0.0 .or. rp_g_in <= 0.0) then
        status = 1
        return
    end if
    if (rp_gstd_in < 1.0 .or. tol_ov_in <= 0.0) then
        status = 1
        return
    end if
    if (ext_case_in /= 0 .and. ext_case_in /= 1) then
        status = 1
        return
    end if
    if (nsubcl_perc_in <= 0.0 .or. nsubcl_perc_in > 1.0) then
        status = 1
        return
    end if
    if (n_in >= 50 .and. n_in <= 500 .and. int(nsubcl_perc_in*real(n_in)) < 1) then
        status = 1
        return
    end if
    if (max_attempts < 1) then
        status = 1
        return
    end if
    if (overlap_mode_in < 0 .or. overlap_mode_in > 2) then
        status = 1
        return
    end if
    if (overlap_fraction_in < 0.0 .or. overlap_fraction_in >= 0.95) then
        status = 1
        return
    end if
    if (overlap_mean_in < 0.0 .or. overlap_mean_in >= 0.95) then
        status = 1
        return
    end if
    if (overlap_std_in < 0.0) then
        status = 1
        return
    end if
    if (overlap_max_in <= 0.0 .or. overlap_max_in >= 0.95) then
        status = 1
        return
    end if
    if (overlap_mode_in == 2 .and. overlap_mean_in > overlap_max_in) then
        status = 1
        return
    end if

    ! Populate the shared runtime configuration used by the legacy engine.
    N = n_in
    Df = df_in
    kf = kf_in
    rp_g = rp_g_in
    rp_gstd = rp_gstd_in
    Ext_case = ext_case_in
    Nsubcl_perc = nsubcl_perc_in
    tol_ov = tol_ov_in
    Quantity_aggregates = 1
    iter = 1
    random_seed_value = seed_in
    overlap_fraction = overlap_fraction_in
    overlap_mean = overlap_mean_in
    overlap_std = overlap_std_in
    overlap_max = overlap_max_in
    call set_overlap_mode_from_code(overlap_mode_in)

    call allocate_particle_arrays()
    call initialize_rng(seed_in)

    do attempts = 1, max_attempts
        call reset_contact_overlaps()
        R = lognormal_pp_radii(rp_gstd, rp_g, N)
        R = randsample(R, N)

        not_able_cca = .false.
        not_able_pca = .false.
        call CCA_sub(not_able_cca, not_able_pca, .false.)

        if (.not. not_able_cca .and. .not. not_able_pca) then
            x_out = X
            y_out = Y
            z_out = Z
            r_out = R
            n_contacts = contact_count
            if (n_contacts > 0) then
                contact_overlap_out(1:n_contacts) = contact_overlaps(1:n_contacts)
            end if
            status = 0
            return
        end if
    end do

    status = 2
    attempts = max_attempts
end subroutine fracval_generate
