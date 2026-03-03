import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute, GuestOnlyRoute } from "./components";
import { RootLayout } from "./layouts";
import {
  HomePage,
  LoginPage,
  RegisterPage,
  RegisterConfirmPage,
  DashboardPage,
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
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
