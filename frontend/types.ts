export type MatReqItem = {
  name: string;
  target_warehouse: string;
  source_warehouse: string;
  status: string;
  item_group_availability: Record<string, boolean>;
};
