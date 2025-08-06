import {frappeClient} from '../utils/client';
import { getCurrentUser } from './auth';

// Helper to standardize error responses
function handleApiError(error: any) {
  if (error && error.message) {
    return { message: error.message };
  }
  return { message: 'Something went wrong' };
}

// Helper to validate API response
function validateResponse(response: any) {
  if (!response || !response.message) {
    throw new Error('Invalid API response');
  }
  if (response.message.status !== 200) {
    throw response.message;
  }
  return response.message.data;
}

export async function getMaterialRequests(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_material_request_list_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getPrinterList() {
  try {
    const response = await frappeClient.get('pick_stream.api.get_printer_list_view');
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getUserProfile(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_user_profile', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getItemGroups(user: string, materialRequest: string) {
  try {
    const searchParams = { user, mr_name: materialRequest };
    const response = await frappeClient.get('pick_stream.api.get_material_request_available_item_groups_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getItemGroupData(user: string, materialRequest: string, itemGroup: string) {
  try {
    const searchParams = { user, mr_name: materialRequest, item_group: itemGroup };
    const response = await frappeClient.get('pick_stream.api.get_material_request_item_group_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getCrateDetails(crate_code: string) {
  try {
    const user = await getCurrentUser();
    const searchParams = { user, crate_code };
    const response = await frappeClient.get('pick_stream.api.get_crate_details', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getUserCrateItemDetails() {
  try {
    const user = await getCurrentUser();
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_user_active_crate_details', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getNotifications(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_user_notifications', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getPickingViewItem(user: string, mr_name: string, item_group: string, crate_code: string) {
  try {
    const searchParams = { user, mr_name, item_group, crate_code };
    const response = await frappeClient.get('pick_stream.api.get_material_request_picking_view', searchParams);
    if (!response || !response.message) {
      throw new Error('Invalid API response');
    }
    if (response.message.status === 404) {
      throw {
        title: 'Not Found',
        message: "The Stream you are looking for doesn't exist.",
        statusCode: 404,
      };
    } else if (response.message.status === 500) {
      throw {
        title: 'Internal Server Error',
        message: 'An Error occurred on the server side of things.',
        statusCode: 500,
      };
    } else if (response.message.status !== 200) {
      throw response.message;
    }
    return response.message.data;
  } catch (err: any) {
    return handleApiError(err);
  }
}

export async function getItemIdentifierList(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_item_identifier_list', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getVerificationListView(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_verification_list_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getTransitListView(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_transit_list_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getReceivingListView(user: string) {
  try {
    const searchParams = { user };
    const response = await frappeClient.get('pick_stream.api.get_receiving_list_view', searchParams);
    return validateResponse(response);
  } catch (err) {
    return handleApiError(err);
  }
}
