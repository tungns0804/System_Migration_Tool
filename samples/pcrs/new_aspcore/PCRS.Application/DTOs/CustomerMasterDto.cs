// CustomerMasterDto.cs — strongly-typed DTO (thanh phan MOI cua kien truc, chi dung trong Application layer)
namespace PCRS.Application.DTOs
{
    public class CustomerMasterDto
    {
        public CustomerMasterDto(string customerCode, string customerName, string branchCode)
        {
            CustomerCode = customerCode;
            CustomerName = customerName;
            BranchCode = branchCode;
        }

        public string CustomerCode { get; set; }
        public string CustomerName { get; set; }
        public string BranchCode { get; set; }
    }
}
