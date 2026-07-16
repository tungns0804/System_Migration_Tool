// OrderBatchService.cs — sample dot 10: ban chay DINH KY (batch/scheduler) cua
// nghiep vu luu tru don hang cu, duoc TACH ra tu method VB ArchiveOldOrders
// (OrderEntry.vb). Ten PurgeOrders trung khoa voi PurgeOrdersAsync (bo hau to
// Async) nen tool tu gom vao muc "METHOD LIEN QUAN TRUNG TEN".
using MediatR;

namespace PCRS.Application.Services
{
    public class OrderBatchService
    {
        private readonly ISender _mediator;

        // Job chay hang dem: giu don hang 12 thang gan nhat
        public async Task PurgeOrders()
        {
            var archivedCount = await _mediator.Send(new Features.OrderEntry.PurgeOrdersCommand(12));
            Console.WriteLine($"Nightly purge: {archivedCount} orders archived");
        }
    }
}
