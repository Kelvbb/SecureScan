import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute, GuestOnlyRoute } from "./components";
import { RootLayout } from "./layouts";
import {
  HomePage,
  LoginPage,
  RegisterPage,
  RegisterConfirmPage,
  DashboardPage,
  CreateScanPage,
  ScanPreviewPage,
  ScanDetailPage,
  ScanScorePage,
  ScanResultsPage,
  ScanFixesPage,
} from "./views";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: (
          <GuestOnlyRoute>
            <HomePage />
          </GuestOnlyRoute>
        ),
      },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "register/confirm", element: <RegisterConfirmPage /> },
      {
        path: "dashboard",
        element: (
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/new",
        element: (
          <ProtectedRoute>
            <CreateScanPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/:scanId/preview",
        element: (
          <ProtectedRoute>
            <ScanPreviewPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/:scanId",
        element: (
          <ProtectedRoute>
            <ScanDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/:scanId/score",
        element: (
          <ProtectedRoute>
            <ScanScorePage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/:scanId/results",
        element: (
          <ProtectedRoute>
            <ScanResultsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "scans/:scanId/fixes",
        element: (
          <ProtectedRoute>
            <ScanFixesPage />
          </ProtectedRoute>
        ),
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);