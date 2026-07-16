// ProductStockDto.cs — strongly-typed DTO (thanh phan MOI cua kien truc)
namespace PCRS.Application.DTOs
{
    public class ProductStockDto
    {
        public string ProductCode { get; set; } = string.Empty;
        public string WarehouseCode { get; set; } = string.Empty;
        public int Quantity { get; set; }
    }
}
