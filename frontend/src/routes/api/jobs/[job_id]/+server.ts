import { json } from '@sveltejs/kit';
import { API_RUGA_SERVER } from '$env/static/private';

export async function GET({ params }) {
	const response = await fetch(`${API_RUGA_SERVER}/jobs/${params.job_id}`);
	const data = await response.json();
	return json(data, { status: response.status });
}
