// StockAuditService.cs — sample dot 10: PHAN GHI LOG dieu chuyen kho,
// duoc TACH ra tu method VB TransferStock (ProductStock.vb) nhung giu cung ten.
// Nam o folder Services/ (khac folder Features/ProductStock/) — minh hoa
// truong hop 1 method VB -> nhieu method C# o nhieu folder.
using PCRS.Domain.Entities;

namespace PCRS.Application.Services
{
    public class StockAuditService
    {
        private readonly IAppDbContext _context;

        public async Task TransferStock(string productCode, string fromWarehouse, string toWarehouse, int quantity)
        {
            var log = new StockTransferLog();
            log.ProductCode = productCode;
            log.FromWarehouse = fromWarehouse;
            log.ToWarehouse = toWarehouse;
            log.Quantity = quantity;
            log.TransferDate = DateTime.UtcNow;
            _context.StockTransferLogs.Add(log);
            await _context.SaveChangesAsync();
        }
    }
}
