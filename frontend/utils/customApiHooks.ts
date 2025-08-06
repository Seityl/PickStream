import { useQuery, useMutation } from '@tanstack/react-query';
import { frappeClient } from './client';
import { MatReqItem } from '../types';

export function useUserProfile(user: string) {
  return useQuery({
    queryKey: ['userProfile', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_user_profile', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useMaterialRequests(user: string) {
  return useQuery({
    queryKey: ['materialRequests', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_material_request_list_view', { user });
      return (response.message as MatReqItem[]) ?? [];
    },
    enabled: !!user,
  });
}

export function usePrinterList() {
  return useQuery({queryKey: ['printerList'], queryFn: async () => {
    const response = await frappeClient.get('pick_stream.api.get_printer_list_view');
    return response.message;
  }});
}

export function useItemGroups(user: string, materialRequest: string) {
  return useQuery({
    queryKey: ['itemGroups', user, materialRequest],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_material_request_available_item_groups_view', {
        user, mr_name: materialRequest
      });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useItemGroupData(user: string, materialRequest: string, itemGroup: string) {
  return useQuery({
    queryKey: ['itemGroupData', user, materialRequest, itemGroup],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_material_request_item_group_view', {
        user, mr_name: materialRequest, item_group: itemGroup
      });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useCrateDetails(user: string, crate_code: string) {
  return useQuery({queryKey: ['crateDetails', user, crate_code], queryFn: async () => {
    const response = await frappeClient.get('pick_stream.api.get_crate_details', { user, crate_code });
    return response.message;
  }});
}

export function useUserCrateItemDetails(user: string) {
  return useQuery({
    queryKey: ['userCrateItemDetails', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_user_active_crate_details', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useNotifications(user: string) {
  return useQuery({
    queryKey: ['notifications', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_user_notifications', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function usePickingViewItem(user: string, mr_name: string, item_group: string, crate_code: string) {
  return useQuery({
    queryKey: ['pickingViewItem', user, mr_name, item_group, crate_code],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_material_request_picking_view', {
        user, mr_name, item_group, crate_code
      });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useItemIdentifierList(user: string) {
  return useQuery({
    queryKey: ['itemIdentifierList', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_item_identifier_list', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useVerificationListView(user: string) {
  return useQuery({
    queryKey: ['verificationListView', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_verification_list_view', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useTransitListView(user: string) {
  return useQuery({
    queryKey: ['transitListView', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_transit_list_view', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useReceivingListView(user: string) {
  return useQuery({
    queryKey: ['receivingListView', user],
    queryFn: async () => {
      const response = await frappeClient.get('pick_stream.api.get_receiving_list_view', { user });
      return response.message;
    },
    enabled: !!user,
  });
}

export function useItemIdentifierDetails(identifier: string) {
  return useQuery({queryKey: ['itemIdentifierDetails', identifier], queryFn: async () => {
    const response = await frappeClient.get('pick_stream.api.get_item_identifier_details', {
      item_identifier: identifier
    });
    return response.message;
  }});
}

export function useSubmitPrintRequest() {
  return useMutation({mutationFn: (data: any) => frappeClient.post('pick_stream.api.submit_print_request', data)});
}

export function useCloseCrate() {
  return useMutation({mutationFn: (data: any) => frappeClient.post('pick_stream.api.submit_close_crate_request', data)});
}

export function useSubmitVerification() {
  return useMutation({mutationFn: (data: any) => frappeClient.post('pick_stream.api.submit_verification_request', data)});
}

export function useSubmitTransit() {
  return useMutation({mutationFn: (data: { 
    user: string, 
    to_warehouse: string, 
    from_warehouse: string, 
    crate_codes?: string[], 
    identifier_codes?: string[] 
  }) => frappeClient.post('pick_stream.api.submit_transit_request', data)});
}
