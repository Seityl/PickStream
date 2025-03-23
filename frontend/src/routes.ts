import {
  type RouteConfig,
  index,
  route,
  layout,
  prefix,
} from "@react-router/dev/routes";

export default [
  route("/login", "./routes/auth/Login.tsx"),
  layout("./layouts/ProtectedLayout,tsx", [
    index("./routes/Home.tsx"), 
    route("/notifications", "./routes/Notifications.tsx"),
    route("/profile", "./routes/Profile.tsx"),
    ...prefix("material-requests", [  
      index("./routes/material-requests/Home.tsx"),
      route(":material_request", "./routes/material-requests/ItemGroupsView.tsx.")
    ]),
    ...prefix("picking", [
      index("./routes/picking/PickingView.tsx"),
    ])
  ]),
] satisfies RouteConfig;
