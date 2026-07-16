// BaseEntity.cs — base class cho moi entity (audit fields + soft delete) — PCRS.Domain
// Thanh phan MOI cua kien truc, khong co ben VB.NET. Nam ngoai Business Logic (Application).
namespace PCRS.Domain.Common
{
    public abstract class BaseEntity
    {
        public DateTime CreatedAt { get; set; }
        public string CreatedBy { get; set; } = string.Empty;
        public DateTime? UpdatedAt { get; set; }
        public string UpdatedBy { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
    }
}
