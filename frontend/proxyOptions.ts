const common_site_config = require("../../../sites/common_site_config.json");
const { webserver_port } = common_site_config;

export default {
  '^/(app|api|assets|files|private)': {
		target: `http://127.0.0.1:${webserver_port}`,
		ws: true,
		// changeOrigin: true,
		// secure: false,
		router: function (req: any) {
			const site_name = req.headers.host.split(':')[0];
			return `http://${site_name}:${webserver_port}`;
		}
	}
}
// import path from 'node:path';
// import fs from 'node:fs';


// function getCommonSiteConfig() {
//   let currentDir = path.resolve('.')
//   // traverse up till we find frappe-bench with sites directory
//   while (currentDir !== '/') {
//     if (
//       fs.existsSync(path.join(currentDir, 'sites')) &&
//       fs.existsSync(path.join(currentDir, 'apps'))
//     ) {
//       let configPath = path.join(currentDir, 'sites', 'common_site_config.json')
//       if (fs.existsSync(configPath)) {
//         return JSON.parse(fs.readFileSync(configPath))
//       }
//       return null
//     }
//     currentDir = path.resolve(currentDir, '..')
//   }
//   return null
// }

// const config = getCommonSiteConfig()
// const webserver_port = config ? config.webserver_port : 8000
// if (!config) {
//   console.log('No common_site_config.json found, using default port 8000')
// }

// export default {
// 	'^/(app|api|assets|files|private)': {
// 		target: `http://127.0.0.1:${webserver_port}`,
// 		ws: true,
// 		changeOrigin: true,
// 		secure: false,
// 		router: function (req: any) {
// 			const site_name = req.headers.host.split(':')[0];
// 			return `http://${site_name}:${webserver_port}`;
// 		}
// 	}
// };
