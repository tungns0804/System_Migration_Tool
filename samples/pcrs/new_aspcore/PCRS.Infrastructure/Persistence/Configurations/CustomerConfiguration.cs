// CustomerConfiguration.cs — EF Core Fluent API, mapping bang PostgreSQL — PCRS.Infrastructure
// Nam ngoai Business Logic (Application) — tool auto-detect phai bo qua khi danh gia backend.
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using PCRS.Domain.Entities;

namespace PCRS.Infrastructure.Persistence.Configurations
{
    public class CustomerConfiguration : IEntityTypeConfiguration<Customer>
    {
        public void Configure(EntityTypeBuilder<Customer> builder)
        {
            builder.ToTable("m_customer");
            builder.HasKey(c => c.CustomerId);
            builder.Property(c => c.CustomerCode).HasColumnName("customer_code").HasMaxLength(8);
            builder.Property(c => c.CustomerName).HasColumnName("customer_name").HasMaxLength(100);
            builder.HasQueryFilter(c => !c.IsDeleted);
        }
    }
}
