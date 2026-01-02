import { json } from '@sveltejs/kit';
import { API_RUGA_SERVER } from '$env/static/private';



export async function GET({ request }) {

  const url = new URL(request.url);
  const rootPath = url.searchParams.get('root_path');
  if(!rootPath || !(rootPath.length > 2)) {
    return json({ error: 'root_path query parameter is required and must be longer than 2 characters' }, { status: 400 });
  }
	const response = await fetch(`${API_RUGA_SERVER}/files?root_path=${rootPath}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	});

  const data = await response.json();
  console.log('+server - data=', data);

	return json(data, { status: 200 });
}
