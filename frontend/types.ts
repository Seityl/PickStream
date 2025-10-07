// types.ts - Updated to match optimized backend response with detailed reasons

/**
 * Availability status for item groups
 * - 'available': Ready to pick
 * - 'already_picked': Stream exists (not Picking) or Source completed
 * - 'no_stock': No stock available in warehouses
 */
export type AvailabilityStatus = 'available' | 'already_picked' | 'no_stock';

/**
 * Item Group Availability is now a mapping of item group names to their status
 * 
 * UPDATED: Returns status string instead of boolean
 * 
 * Example:
 * {
 *   "Pharmaceuticals": "available",
 *   "Medical Supplies": "already_picked",
 *   "OTC Products": "no_stock"
 * }
 */
export type ItemGroupAvailability = Record<string, AvailabilityStatus>;

/**
 * Material Request Item structure from optimized backend
 */
export interface MatReqItem {
  name: string;
  target_warehouse: string;
  source_warehouse: string;
  status: string;
  item_group_availability: ItemGroupAvailability;
}

/**
 * Helper type for rendering item groups with display properties
 */
export interface ItemGroupDisplay {
  name: string;
  status: AvailabilityStatus;
  available: boolean;  // Computed: status === 'available'
  reason?: string;     // Human-readable reason for unavailability
}