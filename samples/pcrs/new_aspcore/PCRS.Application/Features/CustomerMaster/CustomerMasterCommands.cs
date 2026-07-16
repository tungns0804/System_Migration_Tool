// CustomerMasterCommands.cs — Create / Update / Delete + Handlers (CQRS, MediatR)
// Convert tu Business Logic trong CustomerMaster.vb (code-behind he thong cu).
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.Common.Models;
using PCRS.Domain.Entities;

namespace PCRS.Application.Features.CustomerMaster
{
    public record RegisterCustomerCommand(string CustomerCode, string CustomerName, string BranchCode) : IRequest<Result>;
    public record UpdateCustomerCommand(int CustomerCode, string CustomerName) : IRequest<bool>;
    public record DeleteCustomerCommand(string CustomerCode) : IRequest;

    public class RegisterCustomerCommandHandler : IRequestHandler<RegisterCustomerCommand, Result>
    {
        private readonly IAppDbContext _context;
        private readonly CustomerMasterRules _rules;

        public async Task<Result> Handle(RegisterCustomerCommand request, CancellationToken cancellationToken)
        {
            return await RegisterCustomerAsync(request.CustomerCode, request.CustomerName, request.BranchCode);
        }

        // Convert tu VB RegisterCustomer: MessageBox -> Result.Failure (message tieng Nhat)
        private async Task<Result> RegisterCustomerAsync(string customerCode, string customerName, string branchCode)
        {
            if (await _rules.CheckDuplicateCustomerAsync(customerCode))
            {
                return Result.Failure("得意先コードが既に存在します。");
            }
            _context.Customers.Add(new Customer(customerCode, customerName, branchCode));
            await _context.SaveChangesAsync();
            return Result.Success();
        }
    }

    public class UpdateCustomerCommandHandler : IRequestHandler<UpdateCustomerCommand, bool>
    {
        private readonly IAppDbContext _context;
        private readonly CustomerMasterRules _rules;

        public async Task<bool> Handle(UpdateCustomerCommand request, CancellationToken cancellationToken)
        {
            return await UpdateCustomerAsync(request.CustomerCode, request.CustomerName);
        }

        // LOI CO Y: tham so customerCode bi convert sai kieu String -> int
        private async Task<bool> UpdateCustomerAsync(int customerCode, string customerName)
        {
            if (!await _rules.CheckExistCustomerAsync(customerCode.ToString()))
            {
                return false;
            }
            var customer = await _context.Customers.FirstOrDefaultAsync(c => c.CustomerId == customerCode);
            customer.CustomerName = customerName;
            await _context.SaveChangesAsync();
            return true;
        }
    }

    public class DeleteCustomerCommandHandler : IRequestHandler<DeleteCustomerCommand>
    {
        private readonly IAppDbContext _context;

        public async Task Handle(DeleteCustomerCommand request, CancellationToken cancellationToken)
        {
            await DeleteCustomerAsync(request.CustomerCode);
        }

        // Convert tu VB DeleteCustomer: DELETE vat ly -> soft delete (IsDeleted = true, khong xoa vat ly)
        private async Task DeleteCustomerAsync(string customerCode)
        {
            if (string.IsNullOrEmpty(customerCode))
            {
                return;
            }
            var customer = await _context.Customers.FirstOrDefaultAsync(c => c.CustomerCode == customerCode);
            if (customer == null)
            {
                return;
            }
            customer.IsDeleted = true;
            await _context.SaveChangesAsync();
        }
    }
}
