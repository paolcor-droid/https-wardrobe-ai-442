/** Integration contract only. Do not promote snapshots or demos to live inventory. */
export type CatalogueSegment = "women" | "men" | "unisex";
export type CatalogueProvenance = "synthetic-demo" | "supplier-verified";
export type InventoryStatus = "demo" | "snapshot" | "live";
export type CatalogueItemContract = {
 id:string; title:string; genderSegment:CatalogueSegment;
 category:"top"|"bottom"|"shoe"|"accessory";
 canonicalSubtype:string; colour:string; price:number|null; currency:string;
 imageUrl?:string; sourceType:CatalogueProvenance; inventoryStatus:InventoryStatus;
 supplierName?:string; supplierSku?:string; productUrl?:string;
 lastVerifiedAt?:string; imageRightsVerified?:boolean; stockQuantity?:number;
};
export function canClaimLiveInventory(p:CatalogueItemContract):boolean {
 return p.sourceType==="supplier-verified" && p.inventoryStatus==="live"
   && Boolean(p.supplierName && p.supplierSku && p.lastVerifiedAt && p.imageRightsVerified)
   && typeof p.stockQuantity==="number" && p.stockQuantity>=0;
}
export function isSyntheticSafe(p:CatalogueItemContract):boolean {
 return p.sourceType==="synthetic-demo" && p.inventoryStatus==="demo" && !p.productUrl && !p.supplierSku;
}
