import { apiRequest } from "@/lib/api/client";
import { ApiNotification } from "@/lib/types/api";

export function getNotifications() {
  return apiRequest<ApiNotification[]>("/notifications");
}

export function markNotificationRead(notificationId: string) {
  return apiRequest(`/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}