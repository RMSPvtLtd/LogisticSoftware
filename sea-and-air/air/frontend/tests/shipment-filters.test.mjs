import test from "node:test"
import assert from "node:assert/strict"
import { filterShipments, parseShipmentQuery } from "../src/lib/shipment-filters.ts"

const shipments = [
  { id: 1, customer_id: 10, inquiry_id: 20, job_number: "RQ-1001", stage: "arrival", is_at_risk: true, is_on_hold: false, references: [{ value: "MAWB-AAA" }] },
  { id: 2, customer_id: 11, inquiry_id: 21, job_number: "RQ-1002", stage: "customs_clearance", is_at_risk: false, is_on_hold: true, references: [{ value: "BOX-BBB" }] },
  { id: 3, customer_id: 12, inquiry_id: 22, job_number: "RQ-1003", stage: "departure", is_at_risk: false, is_on_hold: false, references: [] },
  { id: 4, customer_id: 13, inquiry_id: 23, job_number: "RQ-1004", stage: "invoice_to_customer", is_at_risk: false, is_on_hold: false, references: [] },
]

const customers = [
  { id: 10, name: "Acme Foods" },
  { id: 11, name: "Blue Harbor" },
  { id: 12, name: "Cedar Works" },
  { id: 13, name: "Delta Retail" },
]

const inquiries = [
  { id: 20, origin: "Lahore", destination: "Dubai", mode: "air" },
  { id: 21, origin: "Lahore", destination: "Dubai", mode: "sea" },
  { id: 22, origin: "Karachi", destination: "London", mode: "air" },
  { id: 23, origin: "Karachi", destination: "London", mode: "air" },
]

const ids = (params) => filterShipments(shipments, customers, inquiries, parseShipmentQuery(new URLSearchParams(params))).map(({ id }) => id)

test("filters shipment rows by every supported control-tower query", () => {
  assert.deepEqual(ids("search=acme"), [1])
  assert.deepEqual(ids("search=box-bbb"), [2])
  assert.deepEqual(ids("at_risk=true"), [1])
  assert.deepEqual(ids("on_hold=true"), [2])
  assert.deepEqual(ids("mode=sea"), [2])
  assert.deepEqual(ids("origin=Lahore&destination=Dubai"), [1, 2])
  assert.deepEqual(ids("stage=arrival"), [1])
  assert.deepEqual(ids("stage=customs_clearance,departure"), [2, 3])
  assert.deepEqual(ids("search=RQ-1004&mode=sea"), [])
})
