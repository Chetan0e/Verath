import React from 'react';
import { Github, MessageSquare, BookOpen } from 'lucide-react';

const Footer = () => {
    const footerLinks = [
        {
            title: 'Product',
            links: [
                { label: 'Features', href: '#features' },
                { label: 'How it works', href: '#how-it-works' },
                { label: 'Pricing', href: '#pricing' },
            ],
        },
        {
            title: 'Resources',
            links: [
                { label: 'Documentation', href: '#docs' },
                { label: 'GitHub', href: 'https://github.com/Chetan0e/Verath' },
                { label: 'Discord', href: '#discord' },
            ],
        },
        {
            title: 'Company',
            links: [
                { label: 'About', href: '#about' },
                { label: 'Blog', href: '#blog' },
                { label: 'Contact', href: '#contact' },
            ],
        },
    ];

    return (
        <footer className="relative border-t border-white/10 bg-background/50 backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-6 lg:px-12 py-8">

                {/* Top */}
                <div className="flex flex-col md:flex-row justify-between gap-8 mb-8">

                    {/* Brand */}
                    <div className="max-w-xs">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                                <span className="text-white font-bold text-xs">V</span>
                            </div>
                            <span className="text-lg font-semibold text-white tracking-tight">Verath</span>
                        </div>
                        <p className="text-sm text-gray-400 leading-relaxed mt-2">
                            Your intelligent digital memory.
                        </p>
                        <div className="flex items-center gap-3 mt-4">
                            <a href="https://github.com/Chetan0e/Verath" className="w-7 h-7 rounded-lg bg-surface border border-border flex items-center justify-center text-gray-400 hover:text-white transition-all">
                                <Github className="w-3 h-3" />
                            </a>
                            <a href="#discord" className="w-7 h-7 rounded-lg bg-surface border border-border flex items-center justify-center text-gray-400 hover:text-white transition-all">
                                <MessageSquare className="w-3 h-3" />
                            </a>
                            <a href="#docs" className="w-7 h-7 rounded-lg bg-surface border border-border flex items-center justify-center text-gray-400 hover:text-white transition-all">
                                <BookOpen className="w-3 h-3" />
                            </a>
                        </div>
                    </div>

                    {/* Links - 3 columns */}
                    <div className="grid grid-cols-3 gap-8">
                        {footerLinks.map((section) => (
                            <div key={section.title}>
                                <h4 className="text-sm font-semibold text-white mb-4">{section.title}</h4>
                                <ul className="space-y-2">
                                    {section.links.map((link) => (
                                        <li key={link.label}>
                                            <a href={link.href} className="text-sm text-gray-400 hover:text-white transition-colors duration-300">
                                                {link.label}
                                            </a>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Bottom */}
                <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <p className="text-sm text-gray-500">© 2026 Verath. All rights reserved.</p>
                    <div className="flex items-center gap-4">
                        <a href="#" className="text-sm text-gray-500 hover:text-gray-300 transition-colors duration-300">Privacy Policy</a>
                        <a href="#" className="text-sm text-gray-500 hover:text-gray-300 transition-colors duration-300">Terms of Service</a>
                    </div>
                </div>

            </div>
        </footer>
    );
};

export default Footer;