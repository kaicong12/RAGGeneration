import fs from 'fs';
import dotenv from 'dotenv'
import csv from 'csv-parser'
import { DataType, MilvusClient } from "@zilliz/milvus2-sdk-node";
dotenv.config({ path: '../.env' })

const HOST = process.env.HOST || 'localhost'
const PORT = process.env.PORT || '19530'
const address = `${HOST}:${PORT}`
const client = new MilvusClient({ address: address });

const sanitiseCollectionName = collectionName => collectionName.replace(/[^a-zA-Z0-9_]/g, '')
const inputFilePath = process.argv[2]
const _collectionName = process.argv[3]

if (!_collectionName || !inputFilePath) {
  console.error("Usage: node insert.js <inputDirectory> <collectionName>");
  process.exit(1);
}

const collectionName = sanitiseCollectionName(_collectionName)

export const parseCSVData = (filepath) => {
  /**
   * For now this function only supports csv file of a specific columns
   * @param {string} filepath - path to which the csv/json docs is stored
   * @returns {Object[]} An array of objects, each of which represents a row
   */
  // parse csv input
  const data = []
  return new Promise((resolve, reject) => {
    fs.createReadStream(filepath)
      .pipe(csv())
      .on('data', row => {
        // Assuming embeddings are separated by commas and enclosed by []
        const embedding = row.embedding.slice(1, -1).split(',').map(Number);
        const item = {
          content: row.chunks,
          embedding: embedding,
          numToken: row.num_tokens
        }

        data.push(item)
      })
      .on('error', e => {
        reject(e)
      })
      .on('end', () => {
        resolve(data)
      })
  })
}

export const createCollectionIfMissing = async (_collectionName) => {
  const collectionName = sanitiseCollectionName(_collectionName)
  const params = {
    collection_name: collectionName,
    description: "Job Handlers",
    fields: [
      {
        name: 'id',
        description: 'ID field',
        data_type: DataType.Int64,
        is_primary_key: true,
        autoID: true,
      },
      {
        name: 'embedding',
        description: 'Vector field',
        data_type: DataType.FloatVector,
        dim: 1536,
      },
      {
        name: 'content',
        description: 'VarChar field',
        data_type: DataType.VarChar,
        max_length: 30000,
      },
      {
        name: 'numToken',
        description: 'Integer field',
        data_type: DataType.Int64,
        max_length: 2000,
      }
    ],
    enableDynamicField: true
  };

  let collectionExists = await client.hasCollection({
    collection_name: collectionName,
  });

  if (!collectionExists.value) {
    await client.createCollection(params);
    console.log(`Collection ${collectionName} has been created`)
  }

  // create index
  await client.createIndex({
    // required
    collection_name: collectionName,
    // optional fields if you are using milvus v2.2.9+
    field_name: 'embedding',
    index_name: 'myindex',
    index_type: 'HNSW',
    params: { efConstruction: 10, M: 4 },
    metric_type: 'L2',
  });

  // load collection into memory
  await client.loadCollectionSync({
    collection_name: collectionName
  });
}

export const insertData = async (data, _organization) => {

  let collectionName = sanitiseCollectionName(_organization)
  await createCollectionIfMissing(collectionName)

  await client.insert({
    collection_name: collectionName,
    fields_data: data
  });

  // create index
  await client.createIndex({
    // required
    collection_name: collectionName,
    field_name: 'embedding', // optional if you are using milvus v2.2.9+
    index_name: 'myindex', // optional
    index_type: 'HNSW', // optional if you are using milvus v2.2.9+
    params: { efConstruction: 10, M: 4 }, // optional if you are using milvus v2.2.9+
    metric_type: 'L2', // optional if you are using milvus v2.2.9+
  });

  console.log("Done insertion and indexing")
}


const data = await parseCSVData(inputFilePath)
await insertData(data, collectionName)
