const Layout = () => import("@/layout/index.vue");

export default {
  path: "/monitor",
  redirect: "/monitor/dashboard",
  meta: {
    icon: "Menu",
    title: "menus.monitor",
    rank: 10
  },
  children: [
    {
      path: "/monitor/dashboard",
      name: "MonitorDashboard",
      component: () => import("@/views/monitor/dashboard/index.vue"),
      meta: {
        title: "menus.monitorDashboard",
        keepAlive: true
      }
    },
    {
      path: "/monitor/links",
      name: "MonitorLinks",
      component: () => import("@/views/monitor/links/index.vue"),
      meta: {
        title: "menus.monitorLinks",
        keepAlive: true
      }
    },
    {
      path: "/monitor/nodes",
      name: "MonitorNodes",
      component: () => import("@/views/monitor/nodes/index.vue"),
      meta: {
        title: "menus.monitorNodes",
        keepAlive: true
      }
    },
    {
      path: "/monitor/alerts",
      name: "MonitorAlerts",
      component: () => import("@/views/monitor/alerts/index.vue"),
      meta: {
        title: "menus.monitorAlerts",
        keepAlive: true
      }
    }
  ]
} satisfies RouteConfigsTable;