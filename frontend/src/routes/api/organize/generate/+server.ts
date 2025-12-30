import { json } from '@sveltejs/kit';
import { API_RUGA_SERVER } from '$env/static/private';

export async function POST({ request }) {
	const body = await request.json();

	const response = await fetch(`${API_RUGA_SERVER}/organize/generate`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	const data = await response.json();
	return json(data, { status: response.status });
}
