import { json } from '@sveltejs/kit';
import * as mockData from './mock.txt?raw';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export async function POST({ request }) {

  console.log('ask/+server.ts - request=', request);
  console.log('ask/+server.ts - mockData=', mockData.default);

  await delay(2_000); // Simulate network delay

	return json(mockData.default, { status: 200 });
}
