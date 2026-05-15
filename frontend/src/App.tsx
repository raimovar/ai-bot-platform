import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import BotsList from "./pages/BotsList";
import BotEditor from "./pages/BotEditor";
import BotChat from "./pages/BotChat";
import Login from "./pages/Login";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="bots" element={<BotsList />} />
            <Route path="bots/new" element={<BotEditor />} />
            <Route path="bots/:id" element={<BotEditor />} />
            <Route path="bots/:id/chat" element={<BotChat />} />
          </Route>
        </Routes>
        <Toaster position="top-right" />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
