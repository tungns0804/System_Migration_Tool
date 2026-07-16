// OrderEntryDto.cs — strongly-typed DTO (thanh phan MOI cua kien truc)
namespace PCRS.Application.DTOs
{
    public class OrderEntryDto
    {
        public OrderEntryDto(string orderNo, string customerCode, DateTime orderDate, decimal totalAmount)
        {
            OrderNo = orderNo;
            CustomerCode = customerCode;
            OrderDate = orderDate;
            TotalAmount = totalAmount;
        }

        public string OrderNo { get; set; }
        public string CustomerCode { get; set; }
        public DateTime OrderDate { get; set; }
        public decimal TotalAmount { get; set; }
    }

    public class OrderEntryDetailDto
    {
        public string ProductCode { get; set; } = string.Empty;
        public int Quantity { get; set; }
        public decimal Amount { get; set; }
    }
}
