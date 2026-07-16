// Result.cs — Result pattern (thanh phan MOI cua kien truc, khong co ben VB.NET)
// Nghiep vu KHONG throw exception: moi loi nghiep vu tra ve Result.Failure(message tieng Nhat).
namespace PCRS.Application.Common.Models
{
    public class Result
    {
        public bool IsSuccess { get; }
        public string Message { get; }

        protected Result(bool isSuccess, string message)
        {
            IsSuccess = isSuccess;
            Message = message;
        }

        public static Result Success() => new Result(true, string.Empty);

        public static Result Failure(string message) => new Result(false, message);
    }
}
