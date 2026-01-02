import { json } from '@sveltejs/kit';
import { API_RUGA_SERVER } from '$env/static/private';

export async function POST({ request }) {
	try {
		const body = await request.json();

		const response = await fetch(`${API_RUGA_SERVER}/chat`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});

		// If backend returned an error, pass it through
		if (!response.ok) {
			const errorText = await response.text();
			console.error('Chat API error:', response.status, errorText);
			return json(
				{ type: 'error', content: `Backend error: ${response.status} - ${errorText}` },
				{ status: response.status }
			);
		}

		// Stream SSE response directly to client
		return new Response(response.body, {
			headers: {
				'Content-Type': 'text/event-stream',
				'Cache-Control': 'no-cache',
				Connection: 'keep-alive'
			}
		});
	} catch (e) {
		console.error('Chat proxy error:', e);
		return json(
			{ type: 'error', content: `Proxy error: ${e instanceof Error ? e.message : String(e)}` },
			{ status: 500 }
		);
	}
}
