// CustomerDeactivationCommands.cs — sample dot 11: LOGIC A1 cua method VB
// CloseCustomerAccount (CustomerMaster.vb) — vo hieu hoa khach hang.
// Method VB goc chua 2 logic (A1 + A2); ben moi TACH thanh 2 method TEN KHAC:
//   A1 -> DeactivateCustomerAsync (file nay)
//   A2 -> CancelPendingOrdersAsync (Features/OrderEntry/OrderCancellationCommands.cs)
// Khai bao trong method_mapping.csv: CloseCustomerAccount,DeactivateCustomer,CancelPendingOrders
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.Common.Models;

namespace PCRS.Application.Features.CustomerMaster
{
    public record DeactivateCustomerCommand(int CustomerId) : IRequest<Result>;

    public class DeactivateCustomerCommandHandler : IRequestHandler<DeactivateCustomerCommand, Result>
    {
        private readonly IAppDbContext _context;

        public async Task<Result> Handle(DeactivateCustomerCommand request, CancellationToken cancellationToken)
        {
            return await DeactivateCustomerAsync(request.CustomerId);
        }

        // Logic A1: dong tai khoan khach hang (STATUS = '9' + ngay dong)
        private async Task<Result> DeactivateCustomerAsync(int customerId)
        {
            if (customerId <= 0)
            {
                return Result.Failure("顧客IDが不正です。");
            }
            await _context.Customers.Where(c => c.Id == customerId)
                .ExecuteUpdateAsync(c => c.SetProperty(x => x.Status, "9")
                                          .SetProperty(x => x.ClosedDate, DateTime.UtcNow));
            return Result.Success();
        }
    }
}
