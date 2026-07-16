// OrderEntryCommands.cs — Create / Cancel + Handlers (CQRS) cua man hinh OrderEntry
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.Common.Models;
using PCRS.Application.DTOs;
using PCRS.Domain.Entities;

namespace PCRS.Application.Features.OrderEntry
{
    public record RegisterOrderCommand(string OrderNo, string CustomerCode, DateTime OrderDate, List<OrderEntryDetailDto> Details) : IRequest<Result>;
    public record CancelOrderCommand(string OrderNo) : IRequest<bool>;

    public class RegisterOrderCommandHandler : IRequestHandler<RegisterOrderCommand, Result>
    {
        private readonly IAppDbContext _context;
        private readonly OrderEntryRules _rules;

        public async Task<Result> Handle(RegisterOrderCommand request, CancellationToken cancellationToken)
        {
            return await RegisterOrderAsync(request.OrderNo, request.CustomerCode, request.OrderDate, request.Details);
        }

        // Convert tu VB RegisterOrder: DataTable -> List<Dto>, MessageBox -> Result.Failure
        private async Task<Result> RegisterOrderAsync(string orderNo, string customerCode, DateTime orderDate, List<OrderEntryDetailDto> details)
        {
            var totalAmount = 0m;
            foreach (var row in details)
            {
                totalAmount = totalAmount + row.Amount;
            }
            if (!await _rules.CheckOrderLimitAsync(customerCode, totalAmount))
            {
                return Result.Failure("与信限度額を超えています。");
            }
            _context.Orders.Add(new Order(orderNo, customerCode, orderDate, totalAmount));
            await _context.SaveChangesAsync();
            return Result.Success();
        }
    }

    public class ApplyMemberDiscountCommandHandler
    {
        private readonly IAppDbContext _context;

        // Convert tu VB ApplyMemberDiscount (sample dot 4) — QUEN nhanh check memberRank:
        // message "会員ランクが不正です。" bien mat -> tool note RULE JP-MSG
        public async Task<Result> ApplyMemberDiscountAsync(int memberRank, decimal discountRate)
        {
            if (discountRate > 0.3m)
            {
                return Result.Failure("割引率が上限を超えています。");
            }
            decimal finalRate = discountRate * memberRank;
            bool applied = await ApplyDiscountToOrderAsync(memberRank, finalRate);
            return Result.Success();
        }

        private async Task<bool> ApplyDiscountToOrderAsync(int memberRank, decimal finalRate)
        {
            await _context.SaveChangesAsync();
            return true;
        }
    }

    public class CancelOrderCommandHandler : IRequestHandler<CancelOrderCommand, bool>
    {
        private readonly IAppDbContext _context;

        public async Task<bool> Handle(CancelOrderCommand request, CancellationToken cancellationToken)
        {
            return await CancelOrderAsync(request.OrderNo);
        }

        // LOI CO Y: thieu tham so reason (VB co 2 tham so: orderNo, reason) — ly do huy bi bo mat
        private async Task<bool> CancelOrderAsync(string orderNo)
        {
            if (string.IsNullOrEmpty(orderNo))
            {
                return false;
            }
            var order = await _context.Orders.FirstOrDefaultAsync(o => o.OrderNo == orderNo);
            order.Status = "9";
            await _context.SaveChangesAsync();
            return true;
        }
    }
}
