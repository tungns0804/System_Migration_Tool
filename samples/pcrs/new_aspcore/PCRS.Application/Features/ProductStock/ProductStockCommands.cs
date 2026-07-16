// ProductStockCommands.cs — Update + Handler (CQRS) cua man hinh ProductStock
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Domain.Entities;

namespace PCRS.Application.Features.ProductStock
{
    public record UpdateStockCommand(string ProductCode, string WarehouseCode, int Quantity) : IRequest<bool>;

    public class UpdateStockCommandHandler : IRequestHandler<UpdateStockCommand, bool>
    {
        private readonly IAppDbContext _context;

        public async Task<bool> Handle(UpdateStockCommand request, CancellationToken cancellationToken)
        {
            return await UpdateStockAsync(request.ProductCode, request.WarehouseCode, request.Quantity);
        }

        // LOI CO Y: logic bi viet lai khac han ban VB —
        // ban VB CONG DON so luong va kiem tra thieu hang / vuot han muc (MAX_STOCK),
        // ban C# GHI DE so luong truc tiep va khong kiem tra gi ca.
        private async Task<bool> UpdateStockAsync(string productCode, string warehouseCode, int quantity)
        {
            var stock = await _context.Stocks.FirstOrDefaultAsync(s => s.ProductCode == productCode && s.WarehouseCode == warehouseCode);
            if (stock == null)
            {
                stock = new Stock();
                stock.ProductCode = productCode;
                stock.WarehouseCode = warehouseCode;
                _context.Stocks.Add(stock);
            }
            stock.Quantity = quantity;
            await _context.SaveChangesAsync();
            return true;
        }
    }
}
