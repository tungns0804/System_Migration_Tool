' CustomerMaster.vb — Man hinh quan ly duoc y (he thong cu — WinForms VB.NET / .NET Framework 4.8 / Oracle 19c)
' Theo kien truc AS-IS trong documents/04: UI event + data access + business logic tron trong code-behind.
Imports System.Data
Imports Oracle.ManagedDataAccess.Client

Public Class CustomerMaster

    ' [UI Event] Form load — se chuyen thanh OnInitializedAsync() trong CustomerMaster.razor
    Private Sub CustomerMaster_Load(sender As Object, e As EventArgs)
        Dim dt As DataTable = GetCustomerList("")
        grdCustomer.DataSource = dt
    End Sub

    ' [UI Event] F8 = 追加変更削除 (them/sua/xoa) — se chuyen thanh Mediator.Send(Command) trong .razor
    Private Sub F8_Click(sender As Object, e As EventArgs)
        If Not RegisterCustomer(txtCustomerCode.Text, txtCustomerName.Text, cmbBranch.SelectedValue.ToString()) Then
            Exit Sub
        End If
        CustomerMaster_Load(sender, e)
    End Sub

    ' [Business Logic] Check duplicate — ky vong convert DUNG (PASS)
    Public Function CheckDuplicateCustomer(customerCode As String) As Boolean
        Dim count As Integer = 0
        Dim sql As String = "SELECT COUNT(*) FROM M_CUSTOMER WHERE CUSTOMER_CODE = :customerCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                count = CInt(cmd.ExecuteScalar())
            End Using
        End Using
        If count > 0 Then
            Return True
        End If
        Return False
    End Function

    ' [Business Logic] Check exist — ky vong convert DUNG (PASS)
    Public Function CheckExistCustomer(customerCode As String) As Boolean
        Dim count As Integer = 0
        Dim sql As String = "SELECT COUNT(*) FROM M_CUSTOMER WHERE CUSTOMER_CODE = :customerCode AND DELETE_FLAG = 0"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                count = CInt(cmd.ExecuteScalar())
            End Using
        End Using
        Return count > 0
    End Function

    ' [Data Access] Lay danh sach duoc y — ben moi tra ve List(Of Dto) thay DataTable (WARNING co chu dich)
    Public Function GetCustomerList(branchCode As String) As DataTable
        Dim dt As New DataTable()
        Dim sql As String = "SELECT CUSTOMER_CODE, CUSTOMER_NAME, BRANCH_CODE FROM M_CUSTOMER WHERE BRANCH_CODE = NVL(:branchCode, BRANCH_CODE) ORDER BY CUSTOMER_CODE"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("branchCode", branchCode)
                Using adapter As New OracleDataAdapter(cmd)
                    adapter.Fill(dt)
                End Using
            End Using
        End Using
        Return dt
    End Function

    ' [Business Logic] Dang ky duoc y — ben moi dung Result.Failure (message tieng Nhat) thay MessageBox
    Public Function RegisterCustomer(customerCode As String, customerName As String, branchCode As String) As Boolean
        If CheckDuplicateCustomer(customerCode) Then
            MessageBox.Show("得意先コードが既に存在します。")
            Return False
        End If
        Dim sql As String = "INSERT INTO M_CUSTOMER (CUSTOMER_CODE, CUSTOMER_NAME, BRANCH_CODE, CREATED_AT) VALUES (:customerCode, :customerName, :branchCode, SYSDATE)"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                cmd.Parameters.Add("customerName", customerName)
                cmd.Parameters.Add("branchCode", branchCode)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Business Logic] Cap nhat duoc y — ben moi bi convert SAI kieu tham so (FAIL co chu dich)
    Public Function UpdateCustomer(customerCode As String, customerName As String) As Boolean
        If Not CheckExistCustomer(customerCode) Then
            Return False
        End If
        Dim sql As String = "UPDATE M_CUSTOMER SET CUSTOMER_NAME = :customerName WHERE CUSTOMER_CODE = :customerCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerName", customerName)
                cmd.Parameters.Add("customerCode", customerCode)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

    ' [Business Logic] Xoa duoc y — ben moi chuyen DELETE vat ly sang soft delete IsDeleted (WARNING co chu dich)
    Public Sub DeleteCustomer(customerCode As String)
        If String.IsNullOrEmpty(customerCode) Then
            Exit Sub
        End If
        Dim sql As String = "DELETE FROM M_CUSTOMER WHERE CUSTOMER_CODE = :customerCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                cmd.ExecuteNonQuery()
            End Using
        End Using
    End Sub

    ' [Business Logic] Lay ten duoc y — ben moi QUEN chua convert (MISSING co chu dich)
    Public Function GetCustomerName(customerCode As String) As String
        Dim name As String = ""
        Dim sql As String = "SELECT NVL(CUSTOMER_NAME, ' ') FROM M_CUSTOMER WHERE CUSTOMER_CODE = :customerCode"
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            Using cmd As New OracleCommand(sql, conn)
                cmd.Parameters.Add("customerCode", customerCode)
                name = CStr(cmd.ExecuteScalar())
            End Using
        End Using
        Return name
    End Function

    ' [Business Logic — sample dot 11] 1 method VB chua 2 LOGIC, ben C# TACH thanh
    ' 2 method TEN KHAC HOAN TOAN o 2 folder khac nhau:
    '   Logic A1 (vo hieu hoa khach hang) -> DeactivateCustomerAsync
    '       (Features/CustomerMaster/CustomerDeactivationCommands.cs)
    '   Logic A2 (huy don hang dang cho)  -> CancelPendingOrdersAsync
    '       (Features/OrderEntry/OrderCancellationCommands.cs)
    ' Vi ten khac han nhau, PHAI khai bao 1 dong NHIEU COT trong method_mapping.csv:
    '   CloseCustomerAccount,DeactivateCustomer,CancelPendingOrders
    ' (cot 2 = method CHINH de ghep cap; cac cot sau = cac MANH TACH)
    Public Function CloseCustomerAccount(customerId As Integer) As Boolean
        If customerId <= 0 Then
            Return False
        End If
        Using conn As New OracleConnection(ConnectionString)
            conn.Open()
            ' Logic A1: vo hieu hoa khach hang (dong tai khoan)
            Using cmd As New OracleCommand("UPDATE M_CUSTOMER SET STATUS = '9', CLOSED_DATE = SYSDATE WHERE CUSTOMER_ID = :customerId", conn)
                cmd.Parameters.Add("customerId", customerId)
                cmd.ExecuteNonQuery()
            End Using
            ' Logic A2: huy toan bo don hang dang cho cua khach nay
            Using cmd As New OracleCommand("UPDATE T_ORDER SET STATUS = 'CANCELED' WHERE CUSTOMER_ID = :customerId AND STATUS = 'PENDING'", conn)
                cmd.Parameters.Add("customerId", customerId)
                cmd.ExecuteNonQuery()
            End Using
        End Using
        Return True
    End Function

End Class
