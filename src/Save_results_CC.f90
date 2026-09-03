module Save_results_CC
implicit none
contains

subroutine Save_results(X,Y,Z,R,N,iter,output_dir,contact_overlaps,contact_count)
implicit none
integer, intent(in) :: N, iter, contact_count
real, intent(in) :: X(N), Y(N), Z(N), R(N)
real, intent(in) :: contact_overlaps(:)
character(len=*), intent(in) :: output_dir
integer :: i, unit_number, ios
character(len=8) :: group, group_n
character(len=1024) :: output_file, contact_file
character(len=512) :: iomsg_text

write(group,'(I8.8)') iter
write(group_n,'(I8.8)') N

output_file = trim(output_dir)//'/N_'//group_n//'_Agg_'//group//'.dat'

open(newunit=unit_number, file=trim(output_file), status='replace', action='write', &
     iostat=ios, iomsg=iomsg_text)
if (ios /= 0) then
    write(*,'(A)') 'ERROR: Could not open output file: '//trim(output_file)
    write(*,'(A)') '       '//trim(iomsg_text)
    stop 1
end if

do i=1,N
    write(unit_number,*) X(i), Y(i), Z(i), R(i)
end do
close(unit_number)

! Sidecar containing the intended contact-overlap fractions used to build this
! aggregate. The contact sequence follows construction order; a completed
! N-particle tree normally contains N-1 intended contacts.
contact_file = trim(output_dir)//'/N_'//group_n//'_Agg_'//group//'.contacts.csv'
open(newunit=unit_number, file=trim(contact_file), status='replace', action='write', &
     iostat=ios, iomsg=iomsg_text)
if (ios /= 0) then
    write(*,'(A)') 'ERROR: Could not open contact output file: '//trim(contact_file)
    write(*,'(A)') '       '//trim(iomsg_text)
    stop 1
end if
write(unit_number,'(A)') 'contact_index,overlap_fraction'
do i=1,contact_count
    write(unit_number,'(I0,A,ES16.8)') i, ',', contact_overlaps(i)
end do
close(unit_number)

end subroutine Save_results

end module Save_results_CC
