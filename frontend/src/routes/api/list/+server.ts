import { json } from '@sveltejs/kit';
import * as mockData from './mock.json';


export async function GET() {

	return json({ ...mockData }, { status: 200 });
}
