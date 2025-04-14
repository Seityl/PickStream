import type { RouteConfig } from "@react-router/dev/routes";
import { route, layout, index, prefix } from "@react-router/dev/routes";

export default [
  route("/login", "routes/auth/Login.tsx"),
  layout("layouts/ProtectedLayout.tsx", [
    layout("layouts/TabLayout.tsx", [
      index("routes/Home.tsx"),
      route("/notifications", "routes/Notifications.tsx"),
      route("/profile", "routes/Profile.tsx"),
    ]),
    ...prefix("material-requests", [
      index("routes/material-requests/material-requests.tsx"),
      route(":mid", "routes/material-requests/material-request.tsx")
    ]),
    ...prefix("picking", [
      index("routes/picking/picking.tsx")
    ])
  ])
] satisfies RouteConfig;
