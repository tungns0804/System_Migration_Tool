// OrderArchiveCommands.cs — Luu tru + xoa don hang cu (CQRS) — sample dot 10.
// Method VB ArchiveOldOrders bi DOI TEN thanh PurgeOrders* va TACH lam 2:
// phan chinh o day (PurgeOrdersAsync), ban chay batch dinh ky tach sang
// Services/OrderBatchService.cs (PurgeOrders). Ten doi -> can khai bao
// 'ArchiveOldOrders,PurgeOrders' trong samples/pcrs/method_mapping.csv.
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace PCRS.Application.Features.OrderEntry
{
    public record PurgeOrdersCommand(int MonthsToKeep) : IRequest<int>;

    public class PurgeOrdersCommandHandler : IRequestHandler<PurgeOrdersCommand, int>
    {
        private readonly IAppDbContext _context;

        public async Task<int> Handle(PurgeOrdersCommand request, CancellationToken cancellationToken)
        {
            return await PurgeOrdersAsync(request.MonthsToKeep);
        }

        private async Task<int> PurgeOrdersAsync(int monthsToKeep)
        {
            var archivedCount = 0;
            if (monthsToKeep <= 0)
            {
                return 0;
            }
            var cutoff = DateTime.UtcNow.AddMonths(-monthsToKeep);
            var oldOrders = await _context.Orders.Where(o => o.OrderDate < cutoff).ToListAsync();
            foreach (var order in oldOrders)
            {
                _context.OrderArchives.Add(OrderArchive.From(order));
            }
            _context.Orders.RemoveRange(oldOrders);
            archivedCount = oldOrders.Count;
            await _context.SaveChangesAsync();
            return archivedCount;
        }
    }
}
