// OrderEntryQueries.cs — tat ca Query + Handler cua man hinh OrderEntry, kem logic tinh toan thuan
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.DTOs;

namespace PCRS.Application.Features.OrderEntry
{
    public record GetOrderListQuery(DateTime FromDate, DateTime ToDate) : IRequest<List<OrderEntryDto>>;

    public class GetOrderListQueryHandler : IRequestHandler<GetOrderListQuery, List<OrderEntryDto>>
    {
        private readonly IAppDbContext _context;

        public async Task<List<OrderEntryDto>> Handle(GetOrderListQuery request, CancellationToken cancellationToken)
        {
            return await GetOrderListAsync(request.FromDate, request.ToDate);
        }

        // Convert tu VB GetOrderList: DataTable -> List<Dto>, ROWNUM <= 500 -> Take(500)
        private async Task<List<OrderEntryDto>> GetOrderListAsync(DateTime fromDate, DateTime toDate)
        {
            var list = await _context.Orders
                .Where(o => o.OrderDate >= fromDate && o.OrderDate <= toDate)
                .OrderByDescending(o => o.OrderDate)
                .Take(500)
                .Select(o => new OrderEntryDto(o.OrderNo, o.CustomerCode, o.OrderDate, o.TotalAmount))
                .ToListAsync();
            return list;
        }
    }

    // Logic tinh toan thuan (khong phu thuoc DB) — convert truc tiep tu code-behind VB
    public static class OrderCalculator
    {
        // Convert tu VB CalcOrderAmount — ky vong DUNG
        public static decimal CalcOrderAmount(int quantity, decimal unitPrice)
        {
            decimal amount = quantity * unitPrice;
            if (amount < 0)
            {
                amount = 0;
            }
            return amount;
        }

        // LOI CO Y: kieu tra ve bi convert sai Decimal -> int (mat phan le cua thue)
        public static int CalcTax(decimal amount, decimal taxRate)
        {
            var tax = amount * taxRate / 100m;
            return (int)Math.Round(tax, 0);
        }
    }
}
