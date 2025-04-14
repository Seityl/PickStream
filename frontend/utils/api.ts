import {frappeClient} from '../utils/client';

export async function getMaterialRequests(user: string) {
  try {
    const searchParams = {user: user};
    
    const response = await frappeClient.get('pick_stream.api.get_material_request_list_view', searchParams);

    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getPrinterList() {
  try {
    const response = await frappeClient.get('pick_stream.api.get_printer_list_view');

    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getUserProfile(user: string) {
  try {
    const searchParams = {user: user};
    const response = await frappeClient.get('pick_stream.api.get_user_profile', searchParams);

    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getItemGroups(user: string, materialRequest: string) {
  try {
    const searchParams = {
      user: user, 
      mr_name: materialRequest
    };

    const response = await frappeClient.get('pick_stream.api.get_material_request_available_item_groups_view', searchParams);
    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getItemGroupData(user: string, materialRequest: string, itemGroup: string) {
  try {
    const searchParams = {user: user, mr_name: materialRequest, item_group: itemGroup};
    const response = await frappeClient.get('pick_stream.api.get_material_request_item_group_view', searchParams);

    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getNotifications(user: string) {
  try {
    const searchParams = {user: user};
    const response = await frappeClient.get('pick_stream.api.get_user_notifications', searchParams);

    if (response.message.status !== 200) {
      throw {};
    }

    return response.message.data;
  } catch(err) {
    return {message: 'something went wrong'};
  }
}

export async function getPickingViewItem(user: string, mr_name: string, item_group: string, crate_code: string) {
  try {
    const searchParams = {
      user: user,
      mr_name: mr_name,
      item_group: item_group,
      crate_code: crate_code
    };

    const response = await frappeClient.get('pick_stream.api.get_material_request_picking_view', searchParams);
    
    if (response.message.status !== 200) {
      if (response.message.status === 404) {
        throw {
          title: "Not Found",
          message: "The Stream you are looking for doesn't exist.",
          statusCode: 404,

        };
      } else if (response.message.status === 500) {
        throw {
          title: "Internal Server Error",
          message: "An Error occured on the server side of things.",
          statusCode: 500,
        };
      }
    }

    return response.message.data; 
  } catch(err: any) {
    throw {message: err.message};
  }
}  
