' ProductStock.vb — Man hinh ton kho san pham (he thong cu — WinForms VB.NET / Oracle 19c)
Imports System.Data
Imports Oracle.ManagedDataAccess.Client

Public Class ProductStock

    Private Const MAX_STOCK As Integer = 999999

    ' [UI Event] Form load — chuyen thanh OnInitializedAsync() trong ProductStock.razor
    Private Sub ProductStock_Load(sender As Object, e As EventArgs)
        Dim quantity As Integer = GetStockQuantity(txtProductCode.Text, cmbWarehouse.SelectedValue.ToString())
        lblQuantity.Text = quantity.ToString()
    End Sub

    ' [Business Logic] Lay so luong ton kho — ky vong convert DUNG (PASS)
    Public Function GetStockQuantity(productCode As String, warehouseCode As String) As Integer
        Dim quantity As Integer = 0
        Dim sql As String = "SELECT NVL(QUANTITY, 0) FROM T_STOCK WHERE PRODUCT_CODE = :productCode AND WAREHOUSE_CODE = :warehouseCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("productCode", productCode)
                cmd.Parameters.Add("warehouseCode", warehouseCode)
                quantity = CInt(cmd.ExecuteScalar())
            End Using
        End Using
        Return quantity
    End Function

    ' [Business Logic] Cap nhat ton kho (cong don + kiem tra thieu/vuot han muc)
    ' — ben moi bi VIET LAI logic khac han: ghi de so luong, khong kiem tra gi (FAIL co chu dich)
    Public Function UpdateStock(productCode As String, warehouseCode As String, quantity As Integer) As Boolean
        Dim currentQty As Integer = GetStockQuantity(productCode, warehouseCode)
        Dim newQty As Integer = currentQty + quantity
        If newQty < 0 Then
            MessageBox.Show("在庫数量が不足しています。")
            Return False
        End If
        If newQty > MAX_STOCK Then
            MessageBox.Show("在庫数量が上限を超えています。")
            Return False
        End If
        Dim sql As String = "UPDATE T_STOCK SET QUANTITY = :newQty WHERE PRODUCT_CODE = :productCode AND WAREHOUSE_CODE = :warehouseCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("newQty", newQty)
                cmd.Parameters.Add("productCode", productCode)
                cmd.Parameters.Add("warehouseCode", warehouseCode)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Business Logic] Kiem tra thieu hang — ky vong convert DUNG (PASS)
    Public Function CheckStockShortage(productCode As String, warehouseCode As String, requiredQty As Integer) As Boolean
        Dim currentQty As Integer = GetStockQuantity(productCode, warehouseCode)
        If currentQty < requiredQty Then
            Return True
        End If
        Return False
    End Function

    ' [Business Logic — sample dot 3, task 1] Dem san pham theo ten.
    ' Ben moi bi DOI TEN thanh FindProductsAsync -> phai khai bao trong
    ' samples/pcrs/method_mapping.csv; khong co --map se ra MISSING + EXTRA.
    Public Function SearchProductByName(keyword As String) As Integer
        Dim hitCount As Integer = 0
        If keyword Is Nothing OrElse keyword.Trim() = "" Then
            Return 0
        End If
        Dim sql As String = "SELECT COUNT(*) FROM T_PRODUCT WHERE PRODUCT_NAME LIKE :keyword"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("keyword", "%" & keyword & "%")
                hitCount = CInt(cmd.ExecuteScalar())
            End Using
        End Using
        Return hitCount
    End Function

    ' [Business Logic — sample dot 4, rule VB-CINT + VB-INTDIV] Tinh gia lam tron theo lo.
    ' CInt = banker's rounding, \ = chia nguyen — ben C# convert sat nghia nhung
    ' hanh vi lam tron/chia co the khac -> tool phai note RULE de review tay.
    Public Function CalcRoundedPrice(unitPrice As Decimal, quantity As Integer, packSize As Integer) As Integer
        Dim packs As Integer = quantity \ packSize
        Dim total As Decimal = unitPrice * packs
        Dim rounded As Integer = CInt(total)
        Return rounded
    End Function

    ' [Business Logic — sample dot 4, rule SELF-EXCL] Check trung ten san pham khi update.
    ' SQL cu co PRODUCT_ID <> :productId (loai tru chinh minh) — ben C# QUEN dieu kien nay.
    Public Function CheckDuplicateProductName(productId As Integer, productName As String) As Boolean
        Dim count As Integer = 0
        Dim sql As String = "SELECT COUNT(*) FROM T_PRODUCT WHERE PRODUCT_NAME = :productName AND PRODUCT_ID <> :productId"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("productName", productName)
                cmd.Parameters.Add("productId", productId)
                count = CInt(cmd.ExecuteScalar())
            End Using
        End Using
        If count > 0 Then
            Return True
        End If
        Return False
    End Function

    ' [Business Logic — sample dot 10] 1 method VB TACH thanh NHIEU method C#:
    ' ben moi tach lam 2 method o 2 folder khac nhau nhung GIU CUNG TEN goc:
    '   1. TransferStockAsync  (Features/ProductStock/StockTransferCommands.cs) — chuyen kho
    '   2. TransferStock       (Services/StockAuditService.cs) — phan ghi log dieu chuyen duoc tach ra
    ' Trung ten -> tool tu gom nhom "METHOD LIEN QUAN TRUNG TEN", KHONG can khai mapping.
    Public Function TransferStock(productCode As String, fromWarehouse As String, toWarehouse As String, quantity As Integer) As Boolean
        Dim currentQty As Integer = GetStockQuantity(productCode, fromWarehouse)
        If currentQty < quantity Then
            MessageBox.Show("移動元の在庫数量が不足しています。")
            Return False
        End If
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand("UPDATE T_STOCK SET QUANTITY = QUANTITY - :quantity WHERE PRODUCT_CODE = :productCode AND WAREHOUSE_CODE = :fromWarehouse", conn)
                cmd.Parameters.Add("quantity", quantity)
                cmd.Parameters.Add("productCode", productCode)
                cmd.Parameters.Add("fromWarehouse", fromWarehouse)
                cmd.ExecuteNonQuery()
            End Using
            Using cmd As New OracleCommand("UPDATE T_STOCK SET QUANTITY = QUANTITY + :quantity WHERE PRODUCT_CODE = :productCode AND WAREHOUSE_CODE = :toWarehouse", conn)
                cmd.Parameters.Add("quantity", quantity)
                cmd.Parameters.Add("productCode", productCode)
                cmd.Parameters.Add("toWarehouse", toWarehouse)
                cmd.ExecuteNonQuery()
            End Using
            Using cmd As New OracleCommand("INSERT INTO T_STOCK_TRANSFER_LOG (PRODUCT_CODE, FROM_WAREHOUSE, TO_WAREHOUSE, QUANTITY, TRANSFER_DATE) VALUES (:productCode, :fromWarehouse, :toWarehouse, :quantity, SYSDATE)", conn)
                cmd.Parameters.Add("productCode", productCode)
                cmd.Parameters.Add("fromWarehouse", fromWarehouse)
                cmd.Parameters.Add("toWarehouse", toWarehouse)
                cmd.Parameters.Add("quantity", quantity)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Business Logic — sample dot 3, task 5] Tong doanh so thang cua kho.
    ' Ben moi van dung raw SQL nhung con NVL + SYSDATE cua Oracle -> ky vong WARNING.
    Public Function GetMonthlySales(warehouseCode As String, targetMonth As String) As Decimal
        Dim total As Decimal = 0
        Dim sql As String = "SELECT NVL(SUM(AMOUNT), 0) FROM T_SALES WHERE WAREHOUSE_CODE = :warehouseCode AND SALES_MONTH = :targetMonth"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("warehouseCode", warehouseCode)
                cmd.Parameters.Add("targetMonth", targetMonth)
                total = CDec(cmd.ExecuteScalar())
            End Using
        End Using
        Return total
    End Function

End Class
