// CustomerMasterQueries.cs — tat ca Query + Handler (GetList...) cua man hinh CustomerMaster
using MediatR;
using Microsoft.EntityFrameworkCore;
using PCRS.Application.DTOs;

namespace PCRS.Application.Features.CustomerMaster
{
    public record GetCustomerListQuery(string BranchCode) : IRequest<List<CustomerMasterDto>>;

    public class GetCustomerListQueryHandler : IRequestHandler<GetCustomerListQuery, List<CustomerMasterDto>>
    {
        private readonly IAppDbContext _context;

        public async Task<List<CustomerMasterDto>> Handle(GetCustomerListQuery request, CancellationToken cancellationToken)
        {
            return await GetCustomerListAsync(request.BranchCode);
        }

        // Convert tu VB GetCustomerList: DataTable -> List<CustomerMasterDto>, NVL -> ??
        private async Task<List<CustomerMasterDto>> GetCustomerListAsync(string branchCode)
        {
            var list = await _context.Customers
                .Where(c => c.BranchCode == (branchCode ?? c.BranchCode))
                .OrderBy(c => c.CustomerCode)
                .Select(c => new CustomerMasterDto(c.CustomerCode, c.CustomerName, c.BranchCode))
                .ToListAsync();
            return list;
        }
    }
}
