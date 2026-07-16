// Customer.cs — Entity (Business Core / Invariants) — PCRS.Domain
using PCRS.Domain.Common;

namespace PCRS.Domain.Entities
{
    public class Customer : BaseEntity
    {
        public Customer() { }

        public Customer(string customerCode, string customerName, string branchCode)
        {
            CustomerCode = customerCode;
            CustomerName = customerName;
            BranchCode = branchCode;
        }

        public int CustomerId { get; set; }
        public string CustomerCode { get; set; } = string.Empty;
        public string CustomerName { get; set; } = string.Empty;
        public string BranchCode { get; set; } = string.Empty;
        public decimal? CreditLimit { get; set; }
    }

    public class Order : BaseEntity
    {
        public Order() { }

        public Order(string orderNo, string customerCode, DateTime orderDate, decimal totalAmount)
        {
            OrderNo = orderNo;
            CustomerCode = customerCode;
            OrderDate = orderDate;
            TotalAmount = totalAmount;
        }

        public string OrderNo { get; set; } = string.Empty;
        public string CustomerCode { get; set; } = string.Empty;
        public DateTime OrderDate { get; set; }
        public decimal TotalAmount { get; set; }
        public string Status { get; set; } = string.Empty;
    }

    public class Stock : BaseEntity
    {
        public string ProductCode { get; set; } = string.Empty;
        public string WarehouseCode { get; set; } = string.Empty;
        public int Quantity { get; set; }
    }
}
