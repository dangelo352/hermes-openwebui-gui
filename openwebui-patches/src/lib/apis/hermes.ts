const HERMES_API_BASE_URL = (globalThis?.location?.hostname ?? '127.0.0.1') === 'localhost'
	? 'http://localhost:8001/v1/hermes'
	: 'http://127.0.0.1:8001/v1/hermes';

const parseJson = async (res: Response) => {
	if (!res.ok) {
		let detail = 'Hermes request failed';
		try {
			const payload = await res.json();
			detail = payload?.detail ?? payload?.error ?? detail;
		} catch {}
		throw detail;
	}
	return await res.json();
};

export const getHermesOverview = async () => {
	const res = await fetch(`${HERMES_API_BASE_URL}/overview`, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		}
	});
	return await parseJson(res);
};

export const runHermesCommand = async (command: string) => {
	const res = await fetch(`${HERMES_API_BASE_URL}/command`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ command })
	});
	return await parseJson(res);
};
