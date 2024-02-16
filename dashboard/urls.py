from django.urls import path
from . import views
from knox import views as knox_views


urlpatterns = [
    path(
        "login",
        views.LoginView.as_view(),
        name="login",
    ),
    path(
        "logout",
        knox_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "change-password",
        views.ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "account-manager",
        views.AccountManagerView.as_view(),
        name="account-manager",
    ),
    path(
        "all-account-managers",
        views.AllAccountManagers.as_view(),
        name="all-account-managers",
    ),
    path(
        "hiring-members",
        views.HiringMemberView.as_view(),
        name="hiring-members",
    ),
    path(
        "hiring-group",
        views.HiringGroupView.as_view(),
        name="hiring-group",
    ),
    path(
        "select-hiring-group",
        views.SelectHiringGroup.as_view(),
        name="select-hiring-group",
    ),
    path(
        "get-hiring-group/<int:group_id>",
        views.SingleHiringGroupView.as_view(),
        name="get-hiring-group",
    ),
    path(
        "get-hiring-group/<int:group_id>/<int:op_id>",
        views.SingleHiringGroupOPView.as_view(),
        name="get-hiring-group-op",
    ),
    path(
        "op-hiring-group/<int:group_id>/<int:op_id>",
        views.OpenPositionHiringGroupView.as_view(),
        name="op-hiring-group-op",
    ),
    path(
        "add-group-member",
        views.AddGroupMemberView.as_view(),
        name="add-group-member",
    ),
    path(
        "hiring-manager",
        views.HiringManagerView.as_view(),
        name="hiring-manager",
    ),
    path(
        "all-hiring-manager",
        views.GetAllHiringManagerView.as_view(),
        name="all-hiring-manager",
    ),
    path(
        "position-list",
        views.PositionView.as_view(),
        name="position-list",
    ),
    path(
        "qualifying-questions-list",
        views.QualifyingQuestionView.as_view(),
        name="qualifying-questions-list",
    ),
    path(
        "cadidate-data",
        views.CandidateDataView.as_view(),
        name="cadidate-data",
    ),
    path(
        "get-single-cadidate-data/<int:op_id>",
        views.SingleCandidateDataView.as_view(),
        name="get-single-cadidate-data",
    ),
    path(
        "hiring-manager-by-client/<str:id>",
        views.HiringManagerByClient.as_view(),
        name="hiring-manager-by-client",
    ),
    path(
        "client-hr",
        views.ClientHRView.as_view(),
        name="client-hr",
    ),
    path(
        "get-clients-by-ca",
        views.GetClientByClinetAdmin.as_view(),
        name="get-clients-by-ca",
    ),
    path(
        "get-all-client-hr",
        views.GetAllClientHR.as_view(),
        name="get-all-client-hr",
    ),
    path(
        "candidate-marks/<int:op_id>",
        views.CandidateMarksView.as_view(),
        name="candidate-marks",
    ),
    path(
        "candidate-feedback/<int:op_id>",
        views.CandidateFeedback.as_view(),
        name="candidate-feedback",
    ),
    path(
        "all-username",
        views.GetAllUsernamesView.as_view(),
        name="all-username",
    ),
    path(
        "get-account-manager-name",
        views.GetAccountManagerName.as_view(),
        name="get-account-manager-name",
    ),
    # path(
    #     "departments",
    #     views.DepartmentView.as_view(),
    #     name="departments",
    # ),
    # path(
    #     "get-departments/<int:client_id>",
    #     views.GetDepartmentsByClientId.as_view(),
    #     name="get-departments",
    # ),
    # path(
    #     "get-department-by-id/<int:department_id>",
    #     views.GetDepartmentsByDepartmentId.as_view(),
    #     name="get-department-by-id",
    # ),
    path(
        "get-manager-and-member/<int:client>",
        views.GetManagerAndMember.as_view(),
        name="get-manager-and-member",
    ),
    path(
        "change-candidate-status/<int:candidate_id>/<int:op_id>",
        views.ChangeCandidateStatus.as_view(),
        name="change-candidate-status",
    ),
    path(
        "candidate-with-timeline/<int:op_id>",
        views.CandidateWithTimeLine.as_view(),
        name="candidate-with-timeline",
    ),
    path(
        "get-team-by-op-id/<int:op_id>",
        views.GetTeamOfOP.as_view(),
        name="get-team-by-op-id",
    ),
    path(
        "get-client-and-op/<int:op_id>",
        views.GetClientAndOPName.as_view(),
        name="get-client-and-op",
    ),
    path(
        "get-thumbs-by-hm/<int:candidate_id>/<int:hiring_member_id>/<int:op_id>",
        views.GetThumbsByHiringMember.as_view(),
        name="get-thumbs-by-hm",
    ),
    path(
        "create-calendar-event-for-interview/<int:op_id>",
        views.CreateCalendarEventForInterview.as_view(),
        name="create-calendar-event-for-interview",
    ),
    path(
        "get-google-auth",
        views.GetGoogleAuthUrl.as_view(),
        name="get-google-auth",
    ),
    path(
        "get-schedul-for-candidate/<int:candidate_id>",
        views.GetScheduleForCandidate.as_view(),
        name="get-schedul-for-candidate",
    ),
    path(
        "get-schedul-response/<int:op_id>",
        views.GetScheduleResponse.as_view(),
        name="get-schedul-response",
    ),
    path(
        "get-google-auth-response",
        views.GetGoogleAuthUrlResponse.as_view(),
        name="get-google-auth-response",
    ),
    path(
        "get-questions/<int:op_id>",
        views.GetQuestiosView.as_view(),
        name="get-questions",
    ),
    path(
        "add-candidate-detail",
        views.AddCandidateDetailsView.as_view(),
        name="add-candidate-detail",
    ),
    path(
        "get-question-response/<int:candidate_id>",
        views.GetQualifyingResponse.as_view(),
        name="get-question-response",
    ),
    path(
        "get-candidate-docs/<int:candidate_id>",
        views.GetCandidateDocs.as_view(),
        name="get-candidate-docs",
    ),
    path(
        "get-all-candidate",
        views.AllCandidateDataView.as_view(),
        name="get-all-candidate",
    ),
    path(
        "get-candidate-to-associate/<int:op_id>",
        views.GetCandidatesToAssociateView.as_view(),
        name="get-candidate-to-associate",
    ),
    path(
        "associate-candidate/<int:client_id>/<int:op_id>",
        views.AssociateCandidateView.as_view(),
        name="associate-candidate",
    ),
    path(
        "get-candidate-application/<int:candidate_id>",
        views.CandidateApplicationsDataView.as_view(),
        name="get-candidate-application",
    ),
    path(
        "single-candidate-application-data/<int:candidate_id>/<int:op_id>",
        views.CandidateSingleApplicationDatView.as_view(),
        name="single-candidate-application-data",
    ),
    path(
        "candidate-basic-details/<int:candidate_id>",
        views.CandidateBasicDetailView.as_view(),
        name="candidate-basic-details",
    ),
    path(
        "get-candidates-based-on-client/<int:client_id>",
        views.GetCandidatesBasedOnClient.as_view(),
        name="get-candidates-based-on-client",
    ),
    path(
        "search-candidate",
        views.SearchCandidateView.as_view(),
        name="search-candidate",
    ),
    path(
        "employee-schedule",
        views.EmployeeScheduleView.as_view(),
        name="employee-schedule",
    ),
    path(
        "get-hiring-members/<int:op_id>",
        views.GetHiringMemberByOpId.as_view(),
        name="get-hiring-members",
    ),
    path(
        "send-mail",
        views.SendMail.as_view(),
        name="send-mail",
    ),
    path(
        "send-interview-set-mail/<int:op_id>",
        views.SendInterviewSetMail.as_view(),
        name="send-interview-set-mail",
    ),
    path(
        "flexbooker-webhook",
        views.ReceiveWebhook.as_view(),
        name="flexbooker-webhook",
    ),
    path(
        "position-progress/<int:op_id>",
        views.PositionProgress.as_view(),
        name="position-progress",
    ),
    path(
        "withdraw-candidate/<int:op_id>/<int:candidate_id>",
        views.WidhrawCandidate.as_view(),
        name="withdraw-candidate",
    ),
    path(
        "unwithdraw-candidate/<int:op_id>/<int:candidate_id>",
        views.UnWidhrawCandidate.as_view(),
        name="unwithdraw-candidate",
    ),
    path(
        "delete-candidate/<int:op_id>/<int:candidate_id>",
        views.DeleteCandidate.as_view(),
        name="delete-candidate",
    ),
    path(
        "get-ops-by-client/<int:client_id>",
        views.GetOPbyClientID.as_view(),
        name="get-ops-by-client",
    ),
    path(
        "associate-hiring-group/<int:op_id>/<int:group_id>",
        views.AssociateHiringGroup.as_view(),
        name="associate-hiring-group",
    ),
    path(
        "updated-tnc-status/<str:username>",
        views.UpdateTNCStatus.as_view(),
        name="updated-tnc-status",
    ),
    path(
        "get-zoom-auth-url",
        views.GetZoomAuthURL.as_view(),
        name="get-zoom-auth-url",
    ),
    path(
        "create-zoom-meeting",
        views.CreateZoomMeeting.as_view(),
        name="create-zoom-meeting",
    ),
    path(
        "duplicate-op/<int:op_id>",
        views.DuplicateOpenPositionView.as_view(),
        name="duplicate-op",
    ),
    path(
        "get-notification/<int:op_id>",
        views.GetNotificationsView.as_view(),
        name="get-notification",
    ),
    path(
        "save-response/<int:op_id>",
        views.SaveResponseView.as_view(),
        name="save-response",
    ),
    path(
        "hire-candidate/<int:op_id>/<int:candidate_id>",
        views.HireCandidateView.as_view(),
        name="hire-candidate",
    ),
    path(
        "offer-candidate/<int:op_id>/<int:candidate_id>",
        views.OfferCandidateView.as_view(),
        name="offer-candidate",
    ),
    path(
        "get-dashboard-data-view",
        views.GetDashboardDataView.as_view(),
        name="get-dashboard-data-view",
    ),
    path(
        "client-admin-dashboard",
        views.ClientAdminDashboardView.as_view(),
        name="client-admin-dashboard",
    ),
    path(
        "withdraw-hiring-member/<int:op_id>/<int:member_id>",
        views.WithdrawHiringMemberView.as_view(),
        name="withdraw-hiring-member",
    ),
    path(
        "restore-hiring-member/<int:op_id>/<int:member_id>",
        views.RestoreHiringMemberView.as_view(),
        name="restore-hiring-member",
    ),
    path(
        "schedule-template",
        views.ScheduleTemplateView.as_view(),
        name="schedule-template",
    ),
    path(
        "all-schedule-template",
        views.AllScheduleTemplateView.as_view(),
        name="all-schedule-template",
    ),
    path(
        "htm-weightage/<int:op_id>/<int:htm_id>",
        views.HTMWeightageView.as_view(),
        name="htm-weightage",
    ),
    path(
        "get-htm-calendar/<int:op_id>",
        views.GetHTMCalendarDataView.as_view(),
        name="get-htm-calendar",
    ),
    path(
        "generate-meeting-url",
        views.GenerateZoomMeeting.as_view(),
        name="generate-meeting-url",
    ),
    path(
        "send-email-to-htm",
        views.SendEmailToHTM.as_view(),
        name="send-email-to-htm",
    ),
    path(
        "archieve-op/<int:op_id>",
        views.ArchievePositionView.as_view(),
        name="archieve-op",
    ),
    path(
        "zapier-webhook",
        views.ZapierWebhookView.as_view(),
        name="zapier-webhook",
    ),
    path(
        "selected-analytics",
        views.SelectAnalyticsView.as_view(),
        name="selected-analytics",
    ),
    path(
        "qorums-dashboard",
        views.QorumsDashboardView.as_view(),
        name="qorums-dashboard",
    ),
    path(
        "get-client-dashboard/<int:client_id>",
        views.SingleClientDashboardView.as_view(),
        name="get-client-dashboard",
    ),
    path(
        "all-senior-managers",
        views.AllSeniorManagers.as_view(),
        name="all-senior-managers",
    ),
    path(
        "senior-managers",
        views.SeniorManagerView.as_view(),
        name="senior-managers",
    ),
    path(
        "singup",
        views.SignUpView.as_view(),
        name="singup",
    ),
    path(
        "user-profile/<int:profile_id>",
        views.UserProfileAPI.as_view(),
        name="user-profile",
    ),
    path(
        "update-dark-mode/<int:profile_id>",
        views.UpdateDarkModeAPI.as_view(),
        name="update-dark-mode",
    ),
    path(
        "pro-tip",
        views.ProTipView.as_view(),
        name="pro-tip",
    ),
    path(
        "get-candidate-summary/<int:candidate_id>",
        views.GetCandidateSummaryData.as_view(),
        name="get-candidate-summary",
    ),
    path(
        "get-linkedin-data",
        views.GetLinkedinData.as_view(),
        name="get-linkedin-data",
    ),
    path(
        "create-zoho-meeting",
        views.GenerateZohoMeeting.as_view(),
        name="create-zoho-meeting",
    ),
    path(
        "get-zoho-code",
        views.GetEmbedCode.as_view(),
        name="get-zoho-code",
    ),
    path(
        "cognito-login",
        views.CognitoLoginView.as_view(),
        name="cognito-login",
    ),
    path(
        "get-client-summary",
        views.GetClientSummary.as_view(),
        name="get-client-summary"
    ),
    path(
        "get-interviews-list/<int:candidate_id>",
        views.GetInterviewList.as_view(),
        name="get-interviews-list"
    ),
    path(
        "candidate-schedule",
        views.CandidateScheduleView.as_view(),
        name="candidate-schedule"
    ),
    path(
        "get-position-to-associate/<int:candidate_id>",
        views.GetPositionToAssociate.as_view(),
        name="get-position-to-associate"
    ),
    path(
        "update-interview-response/<int:interview_id>",
        views.UpdateInterviewResp.as_view(),
        name="update-interview-response"
    ),
    path(
        "get-interviewer-slots/<int:htm_id>",
        views.GetInterviewerFreeSlots.as_view(),
        name="get-interviewer-slots"
    ),
    path(
        "get-candidate-calendar/<int:candidate_id>",
        views.GetCandidateCalendar.as_view(),
        name="get-candidate-calendar"
    ),
    path(
        "update-candidate-details",
        views.UpdateCandidateDetail.as_view(),
        name="update-candidate-details"
    ),
    path(
        "mark-pro/<int:candidate_id>",
        views.MarkProMarkettingView.as_view(),
        name="mark-pro"
    ),
    path(
        "pro-marketting/send-mail",
        views.SendProMarkettingEmail.as_view(),
        name="pro-marketting"
    ),
    path(
        "remove-candidate/<int:op_id>/<int:candidate_id>",
        views.RemoveCandidate.as_view(),
        name="remove-candidate"
    ),
    path(
        "get-moderate-token/<int:host_id>",
        views.GetModeratorToken.as_view(),
        name="get-moderate-token"
    ),
    path(
        "generate-meeting",
        views.GenerateMeeting.as_view(),
        name="generate-meeting"
    ),
    path(
        "update-candidate/<int:candidate_id>",
        views.UpdateCandidateData.as_view(),
        name="update-candidate"
    ),
    path(
        "get-all-members/<int:op_id>",
        views.GetCHSM3.as_view(),
        name="get-all-members"
    ),
    path(
        "compare-candidate/<int:op_id>/<int:candidate_id>",
        views.CompareCandidateMarks.as_view(),
        name="compare-candidate"
    ),
    path(
        "evalate-comments",
        views.EvaluationCommentView.as_view(),
        name="evalate-comments"
    ),
    path(
        "candidate-reset-password/<int:candidate_id>",
        views.CandidateChangePassword.as_view(),
        name="candidate-reset-password"
    ),
    
    path(
        "end-meeting/<int:conference_id>",
        views.EndMeetingAPI.as_view(),
        name="end-meeting"
    ),
    path(
        "request-password-reset",
        views.PasswordResetView.as_view(),
        name="request-password-reset"
    ),
    path(
        "forgot-password/<uidb64>/<token>/",
        views.PasswordCheckAndResetView.as_view(),
        name="forgot-password"
    ),
    path(
        "get-position-summary/<int:op_id>",
        views.GetPositionSummary.as_view(),
        name="get-position-summary"
    ),
    path(
        "get-temp-position-summary",
        views.GetTempPositionSummary.as_view(),
        name="get-temp-position-summary"
    ),
    path(
        "get-archived-position/<int:op_id>",
        views.GetArchivedOpenPosition.as_view(),
        name="get-archived-position"
    ),
    path(
        "get-fit-analysis/<int:op_id>",
        views.GetFitAnalysis.as_view(),
        name="get-fit-analysis"
    ),
    path(
        "get-all-opdata/<int:op_id>",
        views.GetAllOPData.as_view(),
        name="get-all-opdata"
    ),
    path(
        "request-position-association/<int:candidate_id>/<int:position>",
        views.RequestPositionAssociation.as_view(),
        name="request-position-association"
    ),
    path(
        "create-multirole-user",
        views.CreateMultiRoleUser.as_view(),
        name="create-multirole-user"
    ),
    path(
        "change-user-role",
        views.ChangeUserRole.as_view(),
        name="change-user-role"
    ),
    path(
        "get-all-users",
        views.GetAllUser.as_view(),
        name="get-all-users"
    ),
    path(
        "get-htm-audit/<int:op_id>",
        views.GetHTMAudit.as_view(),
        name="get-htm-audit"
    ),
    path(
        "get-single-htm-audit/<int:op_id>/<int:htm>",
        views.GetSingleHTMAudit.as_view(),
        name="get-single-htm-audit"
    ),
    path(
        "get-candidate-associate-data/<int:op_id>/<int:candidate_id>",
        views.GetCandidateAssociateData.as_view(),
        name="get-candidate-associate-data"
    ),
    path(
        "fetch-profile-image/<int:candidate_id>",
        views.FetchProfileImage.as_view(),
        name="fetch-profile-image"
    ),
    path(
        "email-template",
        views.EmailTemplateView.as_view(),
        name="email-template"
    ),
    path(
        "all-email-template",
        views.AllEmailTemplateView.as_view(),
        name="all-email-template"
    ),
    path(
        "get-htm-availabilities",
        views.GetHTMAvailability.as_view(),
        name="get-htm-availabilities"
    ),
    path(
        "trash-open-position/<int:op_id>",
        views.TrashPositionView.as_view(),
        name="trash-open-position"
    ),
    path(
        "packages",
        views.PackageView.as_view(),
        name="packages"
    ),
    path(
        "list-packages",
        views.PackageListView.as_view(),
        name="list-packages"
    ),
    path(
        "generate-otp/<int:client_id>",
        views.GenerateOTPView.as_view(),
        name="generate-otp"
    ),
    path(
        "client-package/<int:client_id>",
        views.ClientPackageView.as_view(),
        name="client-package"
    ),
    path(
        "initial-payment/<int:client_id>",
        views.InitialPaymentView.as_view(),
        name="client-package"
    ),
    path(
        "get-current-htm-data/<int:id>",
        views.GetCurrentHTMData.as_view(),
        name="get-current-htm-data"
    ),
    path(
        "extra-accounts/<int:package_id>",
        views.ExtraAccountsPriceView.as_view(),
        name="extra-accounts"
    ),
    path(
        "user-billing",
        views.UserBillingView.as_view(),
        name="user-billing"
    ),
    path(
        "list-clients",
        views.ListClients.as_view(),
        name="list-clients"
    ),
    path(
        "calculate-additional-amt",
        views.CalculateAdditionalAmount.as_view(),
        name="calculate-additional-amt"
    ),
    path(
        "confirm-payment",
        views.ConfirmPayment.as_view(),
        name="confirm-payment"
    ),
    path(
        "invoice-list",
        views.InvoiceListView.as_view(),
        name="invoice-list"
    ),
    path(
        "stripe-webhook",
        views.StripeWebhookView.as_view(),
        name="stripe-webhook"
    ),
    path(
        "generate-invoice/<int:invoice>",
        views.GenerateInvoice.as_view(),
        name="generate-invoice"
    ),
    path(
        "reset-candidate-creds/<int:candidate_id>",
        views.ResendCandidateCreds.as_view(),
        name="reset-candidate-creds"
    ),
    path(
        "get-multiple-questions",
        views.GetMultipleQuestionsView.as_view(),
        name="get-multiple-questions"
    ),
    path(
        "get-single-question",
        views.GetSingleQuestionView.as_view(),
        name="get-single-question"
    ),
    path(
        "get-all-position/<int:client_id>",
        views.GetAllPositionByClient.as_view(),
        name="get-all-position"
    ),
    path(
        "get-all-clients-list",
        views.GetAllClientsList.as_view(),
        name="get-all-clients-list"
    ),
    path(
        "all-candidate-feedback/<int:op_id>",
        views.AllCandidateFeedback.as_view(),
        name="all-candidate-feedback"
    ),
]
