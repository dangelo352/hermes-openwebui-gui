const HERMES_API_ROOT = (globalThis?.location?.hostname ?? '127.0.0.1') === 'localhost'
	? 'http://localhost:8001/v1'
	: 'http://127.0.0.1:8001/v1';
const HERMES_API_BASE_URL = `${HERMES_API_ROOT}/hermes`;

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

export const getHermesConfigFiles = async () => {
	const res = await fetch(`${HERMES_API_BASE_URL}/config-files`, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		}
	});
	return await parseJson(res);
};

export const updateHermesEnvKey = async (key: string, value: string) => {
	const res = await fetch(`${HERMES_API_BASE_URL}/config-files/env`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ key, value })
	});
	return await parseJson(res);
};

export const updateHermesConfigPath = async (path: string, value: any) => {
	const res = await fetch(`${HERMES_API_BASE_URL}/config-files/config`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ path, value })
	});
	return await parseJson(res);
};

export const getHermesUpdateRebuildStatus = async () => {
	const res = await fetch(`${HERMES_API_ROOT}/admin/update-rebuild`, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		}
	});
	return await parseJson(res);
};

export const triggerHermesUpdateRebuild = async (git_pull = true) => {
	const res = await fetch(`${HERMES_API_ROOT}/admin/update-rebuild`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ git_pull })
	});
	return await parseJson(res);
};
