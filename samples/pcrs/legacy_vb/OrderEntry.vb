' OrderEntry.vb — Man hinh nhap don hang (he thong cu — WinForms VB.NET / Oracle 19c)
Imports System.Data
Imports Oracle.ManagedDataAccess.Client

Public Class OrderEntry

    Private Const MAX_ORDER_LINES As Integer = 200

    ' [UI Event] Form load — chuyen thanh OnInitializedAsync() trong OrderEntry.razor
    Private Sub OrderEntry_Load(sender As Object, e As EventArgs)
        Dim dt As DataTable = GetOrderList(DateTime.Today.AddMonths(-1), DateTime.Today)
        grdOrder.DataSource = dt
    End Sub

    ' [UI Event] Nhap so luong — chuyen thanh @bind-Value:after trong .razor
    Private Sub txtQuantity_TextChanged(sender As Object, e As EventArgs)
        Dim quantity As Integer = CInt(txtQuantity.Text)
        lblAmount.Text = CalcOrderAmount(quantity, CDec(txtUnitPrice.Text)).ToString()
    End Sub

    ' [Business Logic] Tinh tien don hang — ky vong convert DUNG (PASS)
    Public Function CalcOrderAmount(quantity As Integer, unitPrice As Decimal) As Decimal
        Dim amount As Decimal = quantity * unitPrice
        If amount < 0 Then
            amount = 0
        End If
        Return amount
    End Function

    ' [Business Logic] Tinh thue — ben moi bi convert SAI kieu tra ve Decimal -> int (FAIL co chu dich)
    Public Function CalcTax(amount As Decimal, taxRate As Decimal) As Decimal
        Dim tax As Decimal = amount * taxRate / 100D
        Return Math.Round(tax, 0)
    End Function

    ' [Business Logic] Kiem tra han muc tin dung — ky vong convert DUNG (PASS)
    Public Function CheckOrderLimit(customerCode As String, orderAmount As Decimal) As Boolean
        Dim creditLimit As Decimal = 0
        Dim sql As String = "SELECT NVL(CREDIT_LIMIT, 0) FROM M_CUSTOMER WHERE CUSTOMER_CODE = :customerCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                creditLimit = CDec(cmd.ExecuteScalar())
            End Using
        End Using
        If orderAmount > creditLimit Then
            Return False
        End If
        Return True
    End Function

    ' [Business Logic] Dang ky don hang — ben moi DataTable -> List(Of Dto), Result pattern (WARNING co chu dich)
    Public Function RegisterOrder(orderNo As String, customerCode As String, orderDate As Date, details As DataTable) As Boolean
        Dim totalAmount As Decimal = 0
        For Each row As DataRow In details.Rows
            totalAmount = totalAmount + CDec(row("AMOUNT"))
        Next
        If Not CheckOrderLimit(customerCode, totalAmount) Then
            MessageBox.Show("与信限度額を超えています。")
            Return False
        End If
        Dim sql As String = "INSERT INTO T_ORDER (ORDER_NO, CUSTOMER_CODE, ORDER_DATE, TOTAL_AMOUNT) VALUES (:orderNo, :customerCode, :orderDate, :totalAmount)"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("orderNo", orderNo)
                cmd.Parameters.Add("customerCode", customerCode)
                cmd.Parameters.Add("orderDate", orderDate)
                cmd.Parameters.Add("totalAmount", totalAmount)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Business Logic] Huy don hang — ben moi THIEU tham so reason (FAIL co chu dich)
    Public Function CancelOrder(orderNo As String, reason As String) As Boolean
        If String.IsNullOrEmpty(orderNo) Then
            Return False
        End If
        Dim sql As String = "UPDATE T_ORDER SET STATUS = '9', CANCEL_REASON = :reason WHERE ORDER_NO = :orderNo"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("reason", reason)
                cmd.Parameters.Add("orderNo", orderNo)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Data Access] Danh sach don hang (ROWNUM <= 500) — ben moi DataTable -> List(Of Dto) (WARNING co chu dich)
    Public Function GetOrderList(fromDate As Date, toDate As Date) As DataTable
        Dim dt As New DataTable()
        Dim sql As String = "SELECT ORDER_NO, CUSTOMER_CODE, ORDER_DATE, TOTAL_AMOUNT FROM T_ORDER WHERE ORDER_DATE BETWEEN :fromDate AND :toDate AND ROWNUM <= 500 ORDER BY ORDER_DATE DESC"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("fromDate", fromDate)
                cmd.Parameters.Add("toDate", toDate)
                Using adapter As New OracleDataAdapter(cmd)
                    adapter.Fill(dt)
                End Using
            End Using
        End Using
        Return dt
    End Function

    ' [Business Logic — sample dot 4, rule JP-MSG] Ap dung chiet khau hoi vien.
    ' Ben moi QUEN convert nhanh check memberRank -> message "会員ランクが不正です。"
    ' bien mat -> tool phai note RULE JP-MSG (thieu nhanh check).
    Public Function ApplyMemberDiscount(memberRank As Integer, discountRate As Decimal) As Boolean
        If memberRank < 1 Then
            MessageBox.Show("会員ランクが不正です。")
            Return False
        End If
        If discountRate > 0.3D Then
            MessageBox.Show("割引率が上限を超えています。")
            Return False
        End If
        Dim finalRate As Decimal = discountRate * memberRank
        Dim applied As Boolean = ApplyDiscountToOrder(memberRank, finalRate)
        Return applied
    End Function

    ' [Report] In phieu don hang (ActiveReports) — ben moi chuyen sang FastReport *.frx (MISSING co chu dich)
    Public Sub PrintOrderReport(orderNo As String)
        Dim report As New OrderReport()
        report.OrderNo = orderNo
        report.Run()
        report.Document.Print()
    End Sub

    ' [Business Logic — sample dot 10] 1 method VB TACH + DOI TEN thanh nhieu method C#:
    '   1. PurgeOrdersAsync (Features/OrderEntry/OrderArchiveCommands.cs) — xoa don hang cu
    '   2. PurgeOrders      (Services/OrderBatchService.cs) — ban chay dinh ky (batch) duoc tach ra
    ' Vi TEN BI DOI (ArchiveOldOrders -> PurgeOrders) nen PHAI khai bao 1 dong trong
    ' samples/pcrs/method_mapping.csv; khong co --map se ra MISSING + 2 EXTRA.
    Public Function ArchiveOldOrders(monthsToKeep As Integer) As Integer
        Dim archivedCount As Integer = 0
        If monthsToKeep <= 0 Then
            Return 0
        End If
        Dim sqlBackup As String = "INSERT INTO T_ORDER_ARCHIVE SELECT * FROM T_ORDER WHERE ORDER_DATE < ADD_MONTHS(SYSDATE, -:monthsToKeep)"
        Dim sqlDelete As String = "DELETE FROM T_ORDER WHERE ORDER_DATE < ADD_MONTHS(SYSDATE, -:monthsToKeep)"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sqlBackup, conn)
                cmd.Parameters.Add("monthsToKeep", monthsToKeep)
                cmd.ExecuteNonQuery()
            End Using
            Using cmd As New OracleCommand(sqlDelete, conn)
                cmd.Parameters.Add("monthsToKeep", monthsToKeep)
                archivedCount = cmd.ExecuteNonQuery()
            End Using
        End Using
        Return archivedCount
    End Function

End Class
