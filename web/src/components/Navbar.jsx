import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";

const Navbar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };

        window.addEventListener("scroll", handleScroll);

        return () => {
            window.removeEventListener("scroll", handleScroll);
        };
    }, []);

    const navLinks = [
        { label: "Features", href: "#features" },
        { label: "About", href: "#about" },
        { label: "Docs", href: "#docs" },
    ];

    return (
        <motion.nav
            initial={{ y: -30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500
            ${isScrolled
                    ? "py-3"
                    : "py-5"
                }`}
        >
            <div className="max-w-7xl mx-auto px-6 lg:px-10">

                {/* Navbar Container */}
                <div
                    className={`flex items-center justify-between rounded-2xl border transition-all duration-500
                    ${isScrolled
                            ? "bg-black/40 backdrop-blur-2xl border-white/10 shadow-2xl shadow-purple-500/10 px-6 py-3"
                            : "bg-transparent border-transparent px-2 py-2"
                        }`}
                >

                    {/* Logo */}
                    <motion.div
                        whileHover={{ scale: 1.05 }}
                        className="flex items-center gap-3 cursor-pointer"
                    >
                        <div className="relative">
                            <div className="absolute inset-0 bg-purple-500 blur-xl opacity-50" />

                            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
                                <span className="text-white font-bold text-lg">
                                    V
                                </span>
                            </div>
                        </div>

                        <span className="text-white font-semibold text-xl tracking-tight">
                            Verath
                        </span>
                    </motion.div>

                    {/* Desktop Nav */}
                    <div className="hidden md:flex items-center gap-10">
                        {navLinks.map((link, index) => (
                            <motion.a
                                key={index}
                                href={link.href}
                                whileHover={{ y: -2 }}
                                className="relative text-sm text-gray-300 hover:text-white transition-colors duration-300 group"
                            >
                                {link.label}

                                <span className="absolute -bottom-1 left-0 w-0 h-[2px] bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-300 group-hover:w-full" />
                            </motion.a>
                        ))}
                    </div>

                    {/* CTA */}
                    <div className="hidden md:flex items-center">
                        <motion.button
                            whileHover={{
                                scale: 1.05,
                                boxShadow: "0px 0px 25px rgba(139,92,246,0.5)",
                            }}
                            whileTap={{ scale: 0.95 }}
                            className="relative overflow-hidden px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-500 text-white text-sm font-medium shadow-lg shadow-violet-500/20"
                        >
                            <span className="relative z-10">
                                Get Started
                            </span>

                            <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-300 bg-white/10" />
                        </motion.button>
                    </div>

                    {/* Mobile Button */}
                    <button
                        className="md:hidden text-gray-300 hover:text-white transition-colors"
                        onClick={() =>
                            setIsMobileMenuOpen(!isMobileMenuOpen)
                        }
                    >
                        {isMobileMenuOpen ? (
                            <X className="w-6 h-6" />
                        ) : (
                            <Menu className="w-6 h-6" />
                        )}
                    </button>
                </div>

                {/* Mobile Menu */}
                <AnimatePresence>
                    {isMobileMenuOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.25 }}
                            className="md:hidden mt-4 rounded-2xl border border-white/10 bg-black/50 backdrop-blur-2xl p-6 shadow-2xl"
                        >
                            <div className="flex flex-col gap-5">
                                {navLinks.map((link, index) => (
                                    <a
                                        key={index}
                                        href={link.href}
                                        onClick={() =>
                                            setIsMobileMenuOpen(false)
                                        }
                                        className="text-gray-300 hover:text-white transition-colors duration-300"
                                    >
                                        {link.label}
                                    </a>
                                ))}

                                <button className="mt-2 w-full py-3 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-500 text-white font-medium shadow-lg shadow-violet-500/20">
                                    Get Started
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.nav>
    );
};

export default Navbar;