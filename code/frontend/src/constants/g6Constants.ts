/**
 * G6 Topology Graph Constants
 */

// Node size constants - width and height in pixels
export const G6_NODE_SIZE = [40, 40] as const // [width, height]

// Node size halves for positioning calculations
export const G6_NODE_HALF_WIDTH = G6_NODE_SIZE[0] / 2  // 40
export const G6_NODE_HALF_HEIGHT = G6_NODE_SIZE[1] / 2  // 20