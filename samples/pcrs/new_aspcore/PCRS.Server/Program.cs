// Program.cs — ASP.NET Core Host (PCRS.Server): DI Registration, MediatR / FluentValidation scan assembly
// File nay KHONG thuoc Business Logic — tool auto-detect phai bo qua khi danh gia backend.
using FluentValidation;
using PCRS.Application;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents().AddInteractiveServerComponents();
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(typeof(ApplicationAssemblyMarker).Assembly));
builder.Services.AddValidatorsFromAssembly(typeof(ApplicationAssemblyMarker).Assembly);

var app = builder.Build();
app.MapRazorComponents<PCRS.Client.App>().AddInteractiveServerRenderMode();
app.Run();
