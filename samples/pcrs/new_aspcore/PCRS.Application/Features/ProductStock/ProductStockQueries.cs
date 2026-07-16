// ProductStockQueries.cs — tat ca Query + Handler cua man hinh ProductStock
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace PCRS.Application.Features.ProductStock
{
    public record GetStockQuantityQuery(string ProductCode, string WarehouseCode) : IRequest<int>;

    public class GetStockQuantityQueryHandler : IRequestHandler<GetStockQuantityQuery, int>
    {
        private readonly IAppDbContext _context;

        public async Task<int> Handle(GetStockQuantityQuery request, CancellationToken cancellationToken)
        {
            return await GetStockQuantityAsync(request.ProductCode, request.WarehouseCode);
        }

        // Convert tu VB GetStockQuantity (NVL(QUANTITY, 0) -> ?? 0) — ky vong DUNG
        public async Task<int> GetStockQuantityAsync(string productCode, string warehouseCode)
        {
            var quantity = 0;
            quantity = await _context.Stocks
                .Where(s => s.ProductCode == productCode && s.WarehouseCode == warehouseCode)
                .Select(s => (int?)s.Quantity ?? 0)
                .FirstOrDefaultAsync();
            return quantity;
        }

        // Convert tu VB CheckStockShortage — ky vong DUNG
        public async Task<bool> CheckStockShortageAsync(string productCode, string warehouseCode, int requiredQty)
        {
            var currentQty = await GetStockQuantityAsync(productCode, warehouseCode);
            if (currentQty < requiredQty)
            {
                return true;
            }
            return false;
        }

        // Convert tu VB SearchProductByName — bi DOI TEN khi migrate (sample dot 3, task 1);
        // khai bao trong samples/pcrs/method_mapping.csv de tool ghep dung cap
        public async Task<int> FindProductsAsync(string keyword)
        {
            int hitCount = 0;
            if (keyword == null || keyword.Trim() == "")
            {
                return 0;
            }
            hitCount = await _context.Products
                .Where(p => p.ProductName.Contains(keyword))
                .CountAsync();
            return hitCount;
        }

        // Convert tu VB CalcRoundedPrice (sample dot 4): / cua C# voi int la chia nguyen,
        // (int) cat cut phan thap phan (khac CInt banker's rounding) — can review theo RULE
        public int CalcRoundedPrice(decimal unitPrice, int quantity, int packSize)
        {
            int packs = quantity / packSize;
            decimal total = unitPrice * packs;
            int rounded = (int)total;
            return rounded;
        }

        // Convert tu VB CheckDuplicateProductName (sample dot 4) — QUEN dieu kien
        // p.ProductId != productId (loai tru chinh record khi update) -> RULE SELF-EXCL
        public async Task<bool> CheckDuplicateProductNameAsync(int productId, string productName)
        {
            var count = 0;
            count = await _context.Products.CountAsync(p => p.ProductName == productName);
            if (count > 0)
            {
                return true;
            }
            return false;
        }

        // Convert tu VB GetMonthlySales — van raw SQL nhung QUEN sua NVL/SYSDATE
        // cua Oracle (sample dot 3, task 5) -> tool phai canh bao WARNING
        public async Task<decimal> GetMonthlySalesAsync(string warehouseCode, string targetMonth)
        {
            decimal total = 0;
            var sql = "SELECT NVL(SUM(AMOUNT), 0) FROM T_SALES WHERE WAREHOUSE_CODE = :warehouseCode AND SALES_MONTH = :targetMonth AND SALES_DATE <= SYSDATE";
            total = await _dbSession.ExecuteScalarAsync<decimal>(sql, new { warehouseCode, targetMonth });
            return total;
        }

        // Thanh phan MOI (khong co ben VB): xuat CSV ton kho cho man hinh web
        public async Task<string> ExportStockCsvAsync(string warehouseCode)
        {
            var rows = await _context.Stocks
                .Where(s => s.WarehouseCode == warehouseCode)
                .Select(s => s.ProductCode + "," + s.Quantity)
                .ToListAsync();
            var header = "PRODUCT_CODE,QUANTITY";
            return header + "\n" + string.Join("\n", rows);
        }
    }
}
