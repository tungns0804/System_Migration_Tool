// OrderCancellationCommands.cs — sample dot 11: LOGIC A2 cua method VB
// CloseCustomerAccount (CustomerMaster.vb) — huy toan bo don hang dang cho.
// Day la MANH TACH mang TEN KHAC HOAN TOAN so voi method goc — tool chi noi
// duoc nho khai bao mapping 1-n (cot thu 3 tro di trong method_mapping.csv).
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace PCRS.Application.Features.OrderEntry
{
    public record CancelPendingOrdersCommand(int CustomerId) : IRequest<int>;

    public class CancelPendingOrdersCommandHandler : IRequestHandler<CancelPendingOrdersCommand, int>
    {
        private readonly IAppDbContext _context;

        public async Task<int> Handle(CancelPendingOrdersCommand request, CancellationToken cancellationToken)
        {
            return await CancelPendingOrdersAsync(request.CustomerId);
        }

        // Logic A2: huy don hang dang cho (PENDING -> CANCELED) cua khach
        private async Task<int> CancelPendingOrdersAsync(int customerId)
        {
            var canceled = await _context.Orders
                .Where(o => o.CustomerId == customerId && o.Status == "PENDING")
                .ExecuteUpdateAsync(o => o.SetProperty(x => x.Status, "CANCELED"));
            return canceled;
        }
    }
}
