import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Home } from "./pages/Home";
import { Predict } from "./pages/Predict";

function App() {
	// BASE_URL vem do `base` do Vite; sem o basename as rotas quebram quando o
	// site não está na raiz do domínio (GitHub Pages).
	return (
		<BrowserRouter basename={import.meta.env.BASE_URL}>
			<Routes>
				<Route path="/" element={<Home />} />
				<Route path="/predict" element={<Predict />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;
