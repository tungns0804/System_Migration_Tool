// CustomerMasterValidators.cs — FluentValidation + shared helper cua man hinh CustomerMaster
using FluentValidation;
using Microsoft.EntityFrameworkCore;

namespace PCRS.Application.Features.CustomerMaster
{
    public class RegisterCustomerCommandValidator : AbstractValidator<RegisterCustomerCommand>
    {
        public RegisterCustomerCommandValidator()
        {
            RuleFor(x => x.CustomerCode).NotEmpty().WithMessage("得意先コードを入力してください。");
            RuleFor(x => x.CustomerName).NotEmpty().WithMessage("得意先名を入力してください。");
        }
    }

    // Shared helper — cac rule nghiep vu dung chung cho Commands / Validators
    public class CustomerMasterRules
    {
        private readonly IAppDbContext _context;

        // Convert tu VB CheckDuplicateCustomer (SELECT COUNT(*) -> CountAsync)
        public async Task<bool> CheckDuplicateCustomerAsync(string customerCode)
        {
            var count = 0;
            count = await _context.Customers.CountAsync(c => c.CustomerCode == customerCode);
            if (count > 0)
            {
                return true;
            }
            return false;
        }

        // Convert tu VB CheckExistCustomer (DELETE_FLAG = 0 -> global query filter IsDeleted)
        public async Task<bool> CheckExistCustomerAsync(string customerCode)
        {
            var count = 0;
            count = await _context.Customers.CountAsync(c => c.CustomerCode == customerCode);
            return count > 0;
        }

        // Thanh phan MOI (khong co ben VB): kiem tra format ma duoc y theo quy uoc he thong moi
        public bool HasValidCustomerCodeFormat(string customerCode)
        {
            if (string.IsNullOrEmpty(customerCode))
            {
                return false;
            }
            return customerCode.Length == 8;
        }
    }
}
