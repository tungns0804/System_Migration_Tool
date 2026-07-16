// StockTransferCommands.cs — Chuyen kho (CQRS) — sample dot 10.
// Method VB TransferStock duoc TACH lam 2: phan chuyen kho o day,
// phan ghi log dieu chuyen tach sang Services/StockAuditService.cs (CUNG TEN TransferStock).
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.Common.Models;
using PCRS.Application.Services;

namespace PCRS.Application.Features.ProductStock
{
    public record TransferStockCommand(string ProductCode, string FromWarehouse, string ToWarehouse, int Quantity) : IRequest<Result>;

    public class TransferStockCommandHandler : IRequestHandler<TransferStockCommand, Result>
    {
        private readonly IAppDbContext _context;
        private readonly StockAuditService _auditService;

        public async Task<Result> Handle(TransferStockCommand request, CancellationToken cancellationToken)
        {
            return await TransferStockAsync(request.ProductCode, request.FromWarehouse, request.ToWarehouse, request.Quantity);
        }

        private async Task<Result> TransferStockAsync(string productCode, string fromWarehouse, string toWarehouse, int quantity)
        {
            int currentQty = await GetStockQuantityAsync(productCode, fromWarehouse);
            if (currentQty < quantity)
            {
                return Result.Failure("移動元の在庫数量が不足しています。");
            }
            await _context.Stocks.Where(s => s.ProductCode == productCode && s.WarehouseCode == fromWarehouse).ExecuteUpdateAsync(s => s.SetProperty(x => x.Quantity, x => x.Quantity - quantity));
            await _context.Stocks.Where(s => s.ProductCode == productCode && s.WarehouseCode == toWarehouse).ExecuteUpdateAsync(s => s.SetProperty(x => x.Quantity, x => x.Quantity + quantity));
            await _auditService.TransferStock(productCode, fromWarehouse, toWarehouse, quantity);
            return Result.Success();
        }
    }
}
