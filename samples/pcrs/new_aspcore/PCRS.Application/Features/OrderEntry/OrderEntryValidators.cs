// OrderEntryValidators.cs — FluentValidation + shared helper cua man hinh OrderEntry
using FluentValidation;
using Microsoft.EntityFrameworkCore;

namespace PCRS.Application.Features.OrderEntry
{
    public class RegisterOrderCommandValidator : AbstractValidator<RegisterOrderCommand>
    {
        public RegisterOrderCommandValidator()
        {
            RuleFor(x => x.OrderNo).NotEmpty().WithMessage("注文番号を入力してください。");
            RuleFor(x => x.Details).NotEmpty().WithMessage("明細を入力してください。");
        }
    }

    // Shared helper — rule nghiep vu dung chung
    public class OrderEntryRules
    {
        private readonly IAppDbContext _context;

        // Convert tu VB CheckOrderLimit (NVL(CREDIT_LIMIT, 0) -> ?? 0) — ky vong DUNG
        public async Task<bool> CheckOrderLimitAsync(string customerCode, decimal orderAmount)
        {
            var creditLimit = 0m;
            creditLimit = await _context.Customers
                .Where(c => c.CustomerCode == customerCode)
                .Select(c => c.CreditLimit ?? 0)
                .FirstOrDefaultAsync();
            if (orderAmount > creditLimit)
            {
                return false;
            }
            return true;
        }
    }
}
