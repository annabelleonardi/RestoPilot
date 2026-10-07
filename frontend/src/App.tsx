import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import Inventory from "./pages/Inventory";
import Menu from "./pages/Menu";
import Reviews from "./pages/Reviews";
import Suppliers from "./pages/Suppliers";
import WhatsAppDemo from "./pages/WhatsAppDemo";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/menu" element={<Menu />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/whatsapp" element={<WhatsAppDemo />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
